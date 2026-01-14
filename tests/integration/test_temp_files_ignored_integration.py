import time
import uuid

from tests.integration.db_utils import db_fetch_statuses


def test_temp_files_should_be_ignored_by_scan(coord, share, cfg, fakes):
    """
    Temp-like names should be filtered out during SMB scan (list_files), so coordinator won't touch them.
    """
    run_id = uuid.uuid4().hex[:8]
    remitter = f"tempfiles-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())

    # Default ignore rules include prefix "~$" and suffixes like ".part", ".tmp".
    f1 = f"~$LOCK_{run_id}_{ts}.xlsx"
    f2 = f"DATA_{run_id}_{ts}.pdf.part"

    rel1 = f"{remitter}/{f1}"
    rel2 = f"{remitter}/{f2}"

    share.write(rel1, b"temp-1")
    share.write(rel2, b"temp-2")
    time.sleep(4.0)  # make them stable; still must be ignored by name

    coord.run_ok()

    assert share.exists_source(rel1)
    assert share.exists_source(rel2)

    rows1 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{f1}%")
    rows2 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{f2}%")
    assert not rows1, f"Temp file should not create DB record: {f1}"
    assert not rows2, f"Temp file should not create DB record: {f2}"

