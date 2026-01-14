import os
import sys
import time
import socket
import subprocess
from pathlib import Path
from typing import Optional

import httpx
import pytest

from tests.integration.it_config import ITConfig
from tests.integration.coord_client import CoordinatorClient
from tests.integration.db_utils import db_delete_statuses
from tests.integration.share_fs import build_share_fs_from_env, RecordingShareFS

FAKE_ITM_PORT = int(os.getenv("IT_FAKE_ITM_PORT", "18081"))
FAKE_IQUBE_PORT = int(os.getenv("IT_FAKE_IQUBE_PORT", "18082"))
FAKE_FOI_PORT = int(os.getenv("IT_FAKE_FOI_PORT", "18083"))


def _load_env_file(path: Path):
    print(f"[IT] loading env file {path}")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split(sep="=", maxsplit=1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        os.environ.setdefault(k, v)


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def _terminate_proc(p: subprocess.Popen, name: str):
    try:
        p.terminate()
        p.wait(timeout=8)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    finally:
        try:
            out = _read_proc_output(p)
            if out:
                print(f"=== {name} stdout (tail) ===")
                print(out)
        except Exception:
            pass


def _wait_http(url: str, timeout_s: float = 15.0):
    deadline = time.time() + timeout_s
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1.5, trust_env=False)
            if r.status_code < 500:
                return
        except Exception as e:
            last_err = e
        time.sleep(0.2)
    raise RuntimeError(f"Timeout waiting for {url}. last_err={last_err}")


def _read_proc_output(p: subprocess.Popen, max_lines: int = 300) -> str:
    if not p.stdout:
        return ""
    lines = []
    for _ in range(max_lines):
        line = p.stdout.readline()
        if not line:
            break
        lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def _looks_like_our_fake_server(port: int) -> bool:
    base = f"http://127.0.0.1:{port}"
    try:
        r = httpx.get(f"{base}/__events", timeout=1.5, trust_env=False)
        if r.status_code != 200:
            return False
        j = r.json()
        return isinstance(j, dict) and isinstance(j.get("events"), list)
    except Exception:
        return False


def _start_vicorn(app_module: str, port: int, name: str) -> Optional[subprocess.Popen]:
    if _port_in_use("127.0.0.1", port):
        # If a previous test run crashed/was interrupted, the fake server process may
        # still be running. Reuse it instead of failing with "port in use".
        if _looks_like_our_fake_server(port):
            print(f"[IT] [{name}] port {port} already has our fake server; reusing it")
            return None
        raise RuntimeError(
            f"[{name}] port {port} is already in use.\n"
            f"Stop existing process, or set IT_FAKE_*_PORT to another port."
        )

    repo_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(repo_root)}
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        app_module,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "info",
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def pytest_sessionstart(session):
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)
    os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
    os.environ.setdefault("no_proxy", "127.0.0.1,localhost")
    repo_root = Path(__file__).resolve().parents[2]
    _load_env_file(repo_root / ".env.it")


@pytest.fixture(scope="session")
def cfg():
    return ITConfig.load()


@pytest.fixture
def coord(cfg):
    c = CoordinatorClient(cfg)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture
def share(cfg):
    """
    Real SMB share handle with per-test cleanup:
    - removes files written by the test from source + archive
    - removes corresponding DB rows (exact file_name match)

    Set IT_KEEP_ARTIFACTS=1 to keep files/DB rows for debugging.
    """
    inner = build_share_fs_from_env()
    rec = RecordingShareFS(inner)

    keep = os.getenv("IT_KEEP_ARTIFACTS", "").strip() in ("1", "true", "True")
    try:
        yield rec
    finally:
        if keep:
            return
        try:
            rec.cleanup_written()
        except Exception:
            pass

        try:
            abs_names = [inner.src(rel) for rel in rec.written_rel_paths]
            db_delete_statuses(cfg.db_url, abs_names)
        except Exception:
            pass


@pytest.fixture(scope="session")
def fakes():
    procs: list[tuple[str, subprocess.Popen]] = []
    try:
        itm = _start_vicorn("tests.integration.fake_itm_app:app", FAKE_ITM_PORT, "fake_itm")
        if itm is not None:
            procs.append(("fake_itm", itm))

        iqube = _start_vicorn("tests.integration.fake_iqube_app:app", FAKE_IQUBE_PORT, "fake_iqube")
        if iqube is not None:
            procs.append(("fake_iqube", iqube))

        itm_base = f"http://127.0.0.1:{FAKE_ITM_PORT}"
        iqube_base = f"http://127.0.0.1:{FAKE_IQUBE_PORT}"

        _wait_http(f"{itm_base}/__events", timeout_s=20)
        _wait_http(f"{iqube_base}/__events", timeout_s=20)

        print(f"[IT] fake ITM running at {itm_base}")
        print(f"[IT] fake Iqube running at {iqube_base}")

        yield {"itm_base": itm_base, "iqube_base": iqube_base, "itm_proc": itm, "iqube_proc": iqube}
    except Exception:
        for name, p in reversed(procs):
            _terminate_proc(p, name)
        raise
    finally:
        for name, p in reversed(procs):
            _terminate_proc(p, name)


@pytest.fixture(autouse=True)
def reset_fakes(fakes):
    r1 = httpx.post(f"{fakes['itm_base']}/__reset", timeout=5.0, trust_env=False)
    r2 = httpx.post(f"{fakes['iqube_base']}/__reset", timeout=5.0, trust_env=False)
    r1.raise_for_status()
    r2.raise_for_status()


@pytest.fixture(scope="session")
def fake_foi():
    """
    Optional fake FOI server.

    To use it, start your local coordinator with:
      FOI_API_URL=http://127.0.0.1:<port>/extract/{remitter}
      ENV=local  (so IdTokenManager doesn't call Google for localhost)

    Then run tests with IT_RUN_FOI_FAILURE_TESTS=1.
    """
    proc = None
    try:
        proc = _start_vicorn("tests.integration.fake_foi_app:app", FAKE_FOI_PORT, "fake_foi")
        base = f"http://127.0.0.1:{FAKE_FOI_PORT}"
        _wait_http(f"{base}/__events", timeout_s=20)
        yield {"base": base, "api_url": f"{base}/extract/{{remitter}}", "proc": proc}
    finally:
        if proc is not None:
            _terminate_proc(proc, "fake_foi")
