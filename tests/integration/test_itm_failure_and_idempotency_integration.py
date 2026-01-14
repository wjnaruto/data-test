import time
import uuid

import httpx

from tests.integration.db_utils import db_fetch_statuses


def _events(base: str) -> list[dict]:
    r = httpx.get(f"{base}/__events", timeout=5.0, trust_env=False)
    r.raise_for_status()
    return r.json().get("events", [])


def _set_itm_failed(itm_base: str, message: str):
    httpx.post(f"{itm_base}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{itm_base}/__mode",
        json={"ok": False, "message": message},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()


def test_itm_failed_file_is_not_archived_and_not_reprocessed(coord, share, cfg, fakes):
    """
    Requirements:
    - If ITM fails, file should remain in source (not archived by category B).
    - Repeated runs must not reprocess the same file again (idempotency).
    """
    run_id = uuid.uuid4().hex[:8]
    remitter = f"itmfail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"ITMFAIL_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-itm-fail")
    time.sleep(4.0)  # SMB stability window

    _set_itm_failed(fakes["itm_base"], message="forced itm failure")

    coord.run_ok()

    itm_1 = _events(fakes["itm_base"])
    iqube_1 = _events(fakes["iqube_base"])

    rows_1 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows_1, "Expected DB records for ITM failure flow"

    assert share.exists_source(rel_path), "ITM failed file should remain in source"
    assert not share.exists_archived_from_source(rel_path), "ITM failed file should not be archived"

    # Run again: should not call ITM again and should not add more DB rows for the same file.
    coord.run_ok()

    itm_2 = _events(fakes["itm_base"])
    if itm_1:
        assert len(itm_2) == len(itm_1), "ITM should not be called again for the same file"

    iqube_2 = _events(fakes["iqube_base"])
    if iqube_1:
        assert len(iqube_2) == len(iqube_1), "IQube should not be called again for the same file"

    rows_2 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert len(rows_2) == len(rows_1), "DB should not add more rows on second run"
