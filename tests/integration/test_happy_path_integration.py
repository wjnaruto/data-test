import time
from pathlib import Path

import httpx

from tests.integration.db_utils import db_fetch_statuses


def _events(base: str) -> list[dict]:
    r = httpx.get(f"{base}/__events", timeout=5.0, trust_env=False)
    r.raise_for_status()
    return r.json().get("events", [])


def _wait_db_status(cfg, file_name_like: str, status: str, timeout_s: float = 90.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rows = db_fetch_statuses(cfg.db_url, file_name_like)
        if any(str(r[1]) == status for r in rows):
            return rows
        time.sleep(0.5)
    raise AssertionError(f"DB status not found within {timeout_s}s, like={file_name_like}, status={status}")


def test_happy_path_seed_file_calls_itm_and_archives(coord, share, cfg, fakes):
    """
    Happy path expectation:
    - FOI extraction succeeds
    - ITM is called once
    - DB has a SUCCESS status
    - No IQube notify
    - File is eventually archived by background archive housekeeping
    """
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests" / "integration" / "files" / "invest@det.com" / "partly form 2024.xlsx"
    content = seed.read_bytes()

    rel_path = "invest@det.com/partly form 2024.xlsx"
    fname = rel_path.split("/")[-1]

    share.write(rel_path, content)
    time.sleep(4.0)  # SMB stability window

    coord.run_ok()

    # Processing should result in SUCCESS and no IQube notify.
    _wait_db_status(cfg, file_name_like=f"%{fname}%", status="success", timeout_s=120.0)
    assert len(_events(fakes["iqube_base"])) == 0, "IQube should not be called on happy path"
    assert len(_events(fakes["itm_base"])) == 1, "Expected exactly 1 ITM submission on happy path"

    # Archive is asynchronous; wait until the file is moved to archive.
    share.wait_moved_to_archive(rel_path, timeout_s=180.0)

