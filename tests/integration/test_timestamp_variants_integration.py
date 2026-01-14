import time
import uuid

from tests.integration.db_utils import db_fetch_statuses


def _wait_db_record(cfg, file_name_like: str, timeout_s: float = 60.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rows = db_fetch_statuses(cfg.db_url, file_name_like)
        if rows:
            return rows
        time.sleep(0.5)
    raise AssertionError(f"DB record not found within {timeout_s}s, like={file_name_like}")


def test_timestamp_8_digits_versions_archive_older_only_process_newest(coord, share, cfg, fakes):
    run_id = uuid.uuid4().hex[:8]
    remitter = f"ts8-{run_id}@det.com"

    old_ts = time.strftime("%Y%m%d", time.gmtime(time.time() - 86400))
    new_ts = time.strftime("%Y%m%d", time.gmtime(time.time()))

    older = f"{remitter}/REPORT_{run_id}_{old_ts}.xlsx"
    newest = f"{remitter}/REPORT_{run_id}_{new_ts}.xlsx"

    share.write(older, b"old-xlsx-content")
    share.write(newest, b"new-xlsx-content")

    # Wait for SMB stability window so old-file archiving isn't skipped by Policy A.
    time.sleep(4.0)

    coord.run_ok()

    share.wait_moved_to_archive(older, timeout_s=120.0)

    newest_name = newest.split("/")[-1]
    _wait_db_record(cfg, file_name_like=f"%{newest_name}%", timeout_s=90.0)

    older_name = older.split("/")[-1]
    rows_old = db_fetch_statuses(cfg.db_url, f"%{older_name}%")
    assert not rows_old, "Did not expect DB record for older file"


def test_timestamp_mixed_8_and_14_digits_archive_older_process_newest(coord, share, cfg, fakes):
    run_id = uuid.uuid4().hex[:8]
    remitter = f"tsmix-{run_id}@det.com"

    old_ts_8 = time.strftime("%Y%m%d", time.gmtime(time.time() - 86400))
    new_ts_14 = time.strftime("%Y%m%d%H%M%S", time.gmtime(time.time()))

    older = f"{remitter}/REPORT_{run_id}_{old_ts_8}.xlsx"
    newest = f"{remitter}/REPORT_{run_id}_{new_ts_14}.xlsx"

    share.write(older, b"old-xlsx-content")
    share.write(newest, b"new-xlsx-content")

    time.sleep(4.0)

    coord.run_ok()

    share.wait_moved_to_archive(older, timeout_s=120.0)

    newest_name = newest.split("/")[-1]
    _wait_db_record(cfg, file_name_like=f"%{newest_name}%", timeout_s=90.0)

    older_name = older.split("/")[-1]
    rows_old = db_fetch_statuses(cfg.db_url, f"%{older_name}%")
    assert not rows_old, "Did not expect DB record for older file"


def test_timestamp_unsupported_format_t_separator_creates_separate_records(coord, share, cfg, fakes):
    """
    Current behavior: filenames like REPORT_YYYYMMDDTHHMMSS.xlsx are NOT grouped by strip_ts_basename,
    so each file is treated as its own "base" and will be processed independently.
    """
    run_id = uuid.uuid4().hex[:8]
    remitter = f"tst-{run_id}@det.com"

    f1 = f"{remitter}/REPORT_{run_id}_20250105T120450.xlsx"
    f2 = f"{remitter}/REPORT_{run_id}_20250105T120451.xlsx"

    share.write(f1, b"content-1")
    share.write(f2, b"content-2")

    time.sleep(4.0)

    coord.run_ok()

    _wait_db_record(cfg, file_name_like=f"%{f1.split('/')[-1]}%", timeout_s=90.0)
    _wait_db_record(cfg, file_name_like=f"%{f2.split('/')[-1]}%", timeout_s=90.0)

