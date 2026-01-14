import json
import uuid
import random
import time
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone


from tests.integration.it_config import ITConfig
from tests.integration.coord_client import CoordinatorClient
from tests.integration.share_fs import build_share_fs_from_env
from tests.integration.db_utils import db_fetch_statuses


@dataclass(frozen=True)
class SeedFile:
    remitter: str
    local_path: Path
    content: bytes


def _load_seed_files() -> list[SeedFile]:
    """
    Seed files under tests/integration/files/<remitter>/*
    Remitter folder names are preserved.
    """
    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / "tests" / "integration" / "files"
    if not base.exists():
        raise RuntimeError(f"Seed folder not found: {base}")

    seeds: list[SeedFile] = []
    for remitter_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        remitter = remitter_dir.name
        for f in sorted(p for p in remitter_dir.iterdir() if p.is_file()):
            seeds.append(SeedFile(remitter=remitter, local_path=f, content=f.read_bytes()))

    if not seeds:
        raise RuntimeError(f"No seed files found under: {base}")
    return seeds


def _format_ts(dt: datetime, with_ms: bool = False) -> str:
    """
    YYYYMMDDHHMMSS or YYYYMMDDHHMMSSmmm (ms)
    """
    base = dt.strftime("%Y%m%d%H%M%S")
    if not with_ms:
        return base
    ms = int(dt.microsecond / 1000)
    return f"{base}{ms:03d}"


def _make_old_new_ts(with_ms: bool = False) -> tuple[str, str]:
    """
    Make sure old_ts < new_ts deterministically.
    Use a small delta.
    """
    # Use UTC+0 to avoid DST weirdness; timestamp string is what matters anyway
    now = datetime.now(timezone.utc)
    # Randomize a bit so each test run is unique even if run_id reused
    # (run_id is random, but this helps in logs)
    jitter_sec = random.randint(0, 30)
    base = now + timedelta(seconds=jitter_sec)

    old_dt = base - timedelta(seconds=5)
    new_dt = base + timedelta(seconds=5)

    return _format_ts(old_dt, with_ms), _format_ts(new_dt, with_ms)


def _make_versioned_name(original_name: str, run_id: str, ts: str) -> str:
    """
    <stem>_<run_id>_<ts>.<ext>
    Timestamp is underscore token (matches your newest-selection logic).
    """
    p = Path(original_name)
    return f"{p.stem}_{run_id}_{ts}{p.suffix}"


def _wait_db_record(cfg: ITConfig, file_name_like: str, timeout_s: float = 60.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rows = db_fetch_statuses(cfg.db_url, file_name_like)
        if rows:
            return rows
        time.sleep(0.5)
    raise AssertionError(f"DB record not found within {timeout_s}s, like={file_name_like}")


def test_seed_files_multi_remitters_timestamp(coord, share, cfg, fakes):
    """
    For each seed file under tests/integration/files/<remitter>/:
    - write 2 versions into SMB source with same run_id and different timestamps:
        older => should be archived (A class, no DB)
        newest => should be processed (B class, DB record expected)
    File names are unique per test run => no cleanup needed.
    """
    random.seed()

    run_id = uuid.uuid4().hex[:8]  # fixed within this test run
    seeds = _load_seed_files()

    # If you want millisecond timestamp, set with_ms=True and ensure your coordinator parser supports it.
    with_ms = False
    ts_old, ts_new = _make_old_new_ts(with_ms=with_ms)

    written = []  # (older_rel, newest_rel, newest_filename)
    for s in seeds:
        orig = s.local_path.name

        older_name = _make_versioned_name(orig, run_id, ts_old)
        newest_name = _make_versioned_name(orig, run_id, ts_new)

        older_rel = f"{s.remitter}/{older_name}"
        newest_rel = f"{s.remitter}/{newest_name}"

        share.write(older_rel, s.content)
        share.write(newest_rel, s.content)

        written.append((older_rel, newest_rel, newest_name))

    # Wait for SMB stability window so old-file archiving isn't skipped by Policy A.
    time.sleep(4.0)

    coord.run_ok()

    # A class: older must be archived (flat archive)
    for older_rel, _, _ in written:
        share.wait_moved_to_archive(older_rel, timeout_s=180.0)

    # B class: newest should appear in DB
    for _, _, newest_name in written:
        _wait_db_record(cfg, file_name_like=f"%{newest_name}%", timeout_s=90.0)
