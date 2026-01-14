import os
import time
import threading
import uuid

import httpx

from tests.integration.db_utils import db_fetch_statuses


def _events(base: str) -> list[dict]:
    r = httpx.get(f"{base}/__events", timeout=5.0, trust_env=False)
    r.raise_for_status()
    return r.json().get("events", [])


def _wait_until(predicate, timeout_s: float = 10.0, interval_s: float = 0.2):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except Exception:
            pass
        time.sleep(interval_s)

    return None


def test_slow_upload_should_be_skipped_until_complete(coord, share, cfg, fakes):
    """
    Policy A:
    - While a big file is being uploaded (partially written / unstable),
      coordinator must SKIP it:
        * no IQUBE submit
        * no ITM notify
        * no DB record
        * no archive move
    - After upload completes, a second run should process it normally.
    """
    run_id = uuid.uuid4().hex[:8]

    remitter = f"slowupload-{run_id}@det.com"
    content = os.urandom(512 * 1024)  # 512KB

    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"slow_upload_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    httpx.post(url=f"{fakes['itm_base']}/__reset", timeout=5.0, trust_env=False)
    httpx.post(url=f"{fakes['iqube_base']}/__reset", timeout=5.0, trust_env=False)

    t = threading.Thread(
        target=share.write_slow,
        kwargs={
            "rel_path": rel_path,
            "content": content,
            "chunk_size": 64 * 1024,  # 64KB
            "sleep_s": 2,
        },
        daemon=True,
    )
    t.start()

    created = _wait_until(lambda: share.exists_source(rel_path), timeout_s=15.0)
    assert created, "Uploading file was not created in source folder in time"

    coord.run_ok()
    time.sleep(1.5)

    assert len(_events(fakes["itm_base"])) == 0, f"ITM should NOT be called for uploading file: {fname}"
    assert len(_events(fakes["iqube_base"])) == 0, f"IQUBE should NOT be called for uploading file: {fname}"

    assert not share.exists_archived_from_source(rel_path), f"Uploading file should NOT be archived: {fname}"

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert not rows, f"DB record should NOT be created for uploading file: {fname}, rows={rows}"

    t.join(timeout=180)
    assert not t.is_alive(), "slow upload thread did not finish in time"

    time.sleep(4.0)

    coord.run_ok()

    def processed_signal():
        rows2 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
        return bool(rows2) or bool(_events(fakes["itm_base"])) or bool(_events(fakes["iqube_base"]))

    ok = _wait_until(processed_signal, timeout_s=60.0)
    assert ok, f"After upload completes, file should be processed on second run: {fname}"
