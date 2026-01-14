import time
import uuid

from tests.integration.db_utils import db_fetch_statuses

def test_case1_timstamp_versions_archive_older_only_process_newest(coord, share, cfg, fakes):
    run_id = uuid.uuid4().hex[:8]
    remitter = f"remitterA-{run_id}"

    ts_old = time.strftime("%Y%m%d%H%M%S", time.gmtime(time.time() - 60))
    ts_new = time.strftime("%Y%m%d%H%M%S", time.gmtime(time.time()))

    older = f"{remitter}/REPORT_{run_id}_{ts_old}.xlsx"
    newest = f"{remitter}/REPORT_{run_id}_{ts_new}.xlsx"

    share.write(older, b"old-xlsx-content")
    share.write(newest, b"new-xlsx-content")

    # Wait for SMB stability window so old-file archiving isn't skipped by Policy A.
    time.sleep(4.0)

    coord.run_ok()

    share.wait_moved_to_archive(older, timeout_s=90)
    
    newest_name = newest.split("/")[-1]
    rows = db_fetch_statuses(cfg.db_url, f"%{newest_name}%")
    assert rows, "Expected DB record for newest file"

    older_name = older.split("/")[-1]
    rows_old = db_fetch_statuses(cfg.db_url, f"%{older_name}%")
    assert not rows_old, "Did not expect DB record for older file"
