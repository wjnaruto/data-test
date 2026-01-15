import os
import time
import uuid

import httpx

from tests.integration.db_utils import db_fetch_statuses


def _events(base: str) -> list[dict]:
    r = httpx.get(f"{base}/__events", timeout=5.0, trust_env=False)
    r.raise_for_status()
    return r.json().get("events", [])


def _require_failpoints_enabled():
    """
    This test requires a local-only failpoint inside `Coordinator._process_one` to deterministically
    raise an unknown exception *after* DB claim but *before* writing final statuses, so the DB tx rolls back.

    Start coordinator with:
      ENV=local
      IT_ENABLE_FAILPOINTS=1
    """
    if os.getenv("IT_ENABLE_FAILPOINTS", "").strip().lower() not in ("1", "true", "yes"):
        import pytest
        pytest.skip("Set IT_ENABLE_FAILPOINTS=1 and start coordinator with the same env to enable rollback failpoints.")


def test_unknown_exception_rolls_back_db_and_allows_reprocess(coord, share, cfg, fakes):
    _require_failpoints_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"txrb-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())

    fname = f"IT_TX_ROLLBACK_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-tx-rollback")
    time.sleep(4.0)  # SMB stability window

    # First run: failpoint raises inside the DB transaction after claim => tx rollback, no DB rows.
    resp1 = coord.run_ok()

    errors = (resp1 or {}).get("error") or []
    assert any("IT_FAILPOINT_TX_ROLLBACK_AFTER_CLAIM" in str(e.get("error") or "") for e in errors), (
        "Failpoint did not trigger. Ensure coordinator is started with ENV=local and IT_ENABLE_FAILPOINTS=1."
    )

    rows1 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert not rows1, f"Expected NO DB rows due to rollback, got: {rows1}"

    assert share.exists_source(rel_path), "File should remain in source after unknown exception"
    assert not share.exists_archived_from_source(rel_path), "File should not be archived after unknown exception"

    assert len(_events(fakes["itm_base"])) == 0, "ITM should not be called when exception happens before extraction"
    assert len(_events(fakes["iqube_base"])) == 0, "IQube should not be called for unknown exception rollback path"

    # Second run: failpoint triggers only once per filename, so coordinator should attempt processing again,
    # leaving at least one DB row (success/failure depends on FOI/ITM env, but it should not be empty).
    coord.run_ok()

    rows2 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows2, "Expected DB rows on second run (file should be reprocessed after rollback)"

