import time
import uuid

import httpx

from tests.integration.db_utils import db_fetch_statuses


def _events(base: str) -> list[dict]:
    r = httpx.get(f"{base}/__events", timeout=5.0, trust_env=False)
    r.raise_for_status()
    return r.json().get("events", [])


def test_unstable_file_should_be_skipped(coord, share, cfg, fakes):
    """
    Policy A: a newly-written file should be considered unstable and skipped for this run:
      - no ITM call
      - no IQube notify
      - no DB record
      - no archive move
    """
    run_id = uuid.uuid4().hex[:8]
    remitter = f"unstable-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"UNSTABLE_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"just-written")
    # Do NOT wait for SMB stability window.
    coord.run_ok()

    assert share.exists_source(rel_path), "File should remain in source (skipped)"
    assert not share.exists_archived_from_source(rel_path), "File should not be archived (skipped)"

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert not rows, f"DB should not create a record for unstable file: rows={rows}"

    assert len(_events(fakes["itm_base"])) == 0, "ITM should not be called for unstable file"
    assert len(_events(fakes["iqube_base"])) == 0, "IQube should not be called for unstable file"
