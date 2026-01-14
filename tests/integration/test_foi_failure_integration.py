import os
import time
import uuid

import httpx

from tests.integration.db_utils import db_fetch_statuses


def _events(base: str) -> list[dict]:
    r = httpx.get(f"{base}/__events", timeout=5.0, trust_env=False)
    r.raise_for_status()
    return r.json().get("events", [])


def _require_foi_failure_tests_enabled():
    if os.getenv("IT_RUN_FOI_FAILURE_TESTS", "").strip() not in ("1", "true", "True"):
        import pytest
        pytest.skip("Set IT_RUN_FOI_FAILURE_TESTS=1 and start coordinator with FOI_API_URL pointing to fake FOI.")


def _has_event_for_filename(events: list[dict], fname: str) -> bool:
    return any(e.get("filename") == fname for e in (events or []))


def _iqube_event_for_file(events: list[dict], fname: str) -> dict | None:
    for e in events or []:
        body = (e or {}).get("body") or {}
        file_path = str(body.get("file_path") or "")
        if fname and fname in file_path:
            return e
    return None


def test_foi_invalid_password_maps_to_password_failed(coord, share, cfg, fakes, fake_foi):
    """
    Requires:
      - `IT_RUN_FOI_FAILURE_TESTS=1`
      - coordinator started with `FOI_API_URL={fake_foi['api_url']}` and `ENV=local`
    """
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_INVALIDPWD_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)  # SMB stability window

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"ok": False, "failure_reason": "invalid password", "detailed_failure_reason": "forced"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    foi_events = _events(fake_foi["base"])
    if not _has_event_for_filename(foi_events, fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    # assert status contains extraction_file_password_failed somewhere
    assert any("extraction_file_password_failed" in str(r[1]) for r in rows)

    # On extraction failure: should notify IQube and should not call ITM.
    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_file_password_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_service_failure_maps_to_service_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_SERVICE_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-service-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"response_type": "non_dict"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    foi_events = _events(fake_foi["base"])
    if not _has_event_for_filename(foi_events, fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_service_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_service_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_no_template_match_maps_to_extraction_file_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_NOTEMPLATE_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"ok": False, "failure_reason": "no matched template", "detailed_failure_reason": "forced"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    if not _has_event_for_filename(_events(fake_foi["base"]), fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_file_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_file_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_data_format_error_maps_to_extraction_file_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_DATAFORMAT_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"ok": False, "failure_reason": "data format error", "detailed_failure_reason": "forced"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    if not _has_event_for_filename(_events(fake_foi["base"]), fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_file_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_file_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_http_422_maps_to_extraction_file_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_HTTP422_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"response_type": "http_422"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    if not _has_event_for_filename(_events(fake_foi["base"]), fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_file_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_file_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_http_400_maps_to_extraction_file_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_HTTP400_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"response_type": "http_400"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    if not _has_event_for_filename(_events(fake_foi["base"]), fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_file_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_file_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_missing_result_maps_to_service_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_MISSINGRESULT_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"response_type": "missing_result"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    if not _has_event_for_filename(_events(fake_foi["base"]), fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_service_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_service_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_empty_result_maps_to_service_failed(coord, share, cfg, fakes, fake_foi):
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_EMPTYRESULT_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"response_type": "empty_result"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    if not _has_event_for_filename(_events(fake_foi["base"]), fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows, "Expected DB record"
    assert any("extraction_service_failed" in str(r[1]) for r in rows)

    assert len(_events(fakes["itm_base"])) == 0
    iq_evt = _iqube_event_for_file(_events(fakes["iqube_base"]), fname)
    assert iq_evt, "Expected IQube notify for extraction failure"
    assert "extraction_service_failed" in str(((iq_evt.get("body") or {}).get("reason") or "")).lower()
    assert share.exists_source(rel_path)
    assert not share.exists_archived_from_source(rel_path)


def test_foi_invalid_password_is_not_reprocessed_on_second_run(coord, share, cfg, fakes, fake_foi):
    """
    Requirement: repeated runs must NOT reprocess the same file again.
    For extraction failures, the initial 'processing' claim row stays in DB and prevents retries.
    """
    _require_foi_failure_tests_enabled()

    run_id = uuid.uuid4().hex[:8]
    remitter = f"foifail-{run_id}@det.com"
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    fname = f"FOI_IDEMPOTENCY_{run_id}_{ts}.pdf"
    rel_path = f"{remitter}/{fname}"

    share.write(rel_path, b"content-for-foi-failure")
    time.sleep(4.0)

    httpx.post(f"{fake_foi['base']}/__reset", timeout=5.0, trust_env=False).raise_for_status()
    httpx.post(
        f"{fake_foi['base']}/__mode",
        json={"ok": False, "failure_reason": "invalid password", "detailed_failure_reason": "forced"},
        timeout=5.0,
        trust_env=False,
    ).raise_for_status()

    coord.run_ok()

    foi_events_1 = _events(fake_foi["base"])
    if not _has_event_for_filename(foi_events_1, fname):
        raise AssertionError(
            "Fake FOI did not receive the upload. Coordinator is not pointing to fake FOI.\n"
            f"Start coordinator with FOI_API_URL={fake_foi['api_url']} and ENV=local."
        )

    rows_1 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert rows_1, "Expected DB record"

    coord.run_ok()

    foi_events_2 = _events(fake_foi["base"])
    assert len(foi_events_2) == len(foi_events_1), "FOI should not be called again on second run"

    rows_2 = db_fetch_statuses(cfg.db_url, file_name_like=f"%{fname}%")
    assert len(rows_2) == len(rows_1), "DB should not add more rows on second run"
