# Coordinator `/coordinator/runs` Integration Test Cases

This document categorizes the integration test cases for the end-to-end coordinator run flow (real SMB + real Postgres, coordinator is called via HTTP).

## Scope: What we are testing

The `/api/v1/coordinator/runs` flow (high level):
1. Scan SMB source folder (with temp-file filtering).
2. Group by `remitter + base_name` and select the newest file (older versions are “scan-candidates” for archiving).
3. Policy A stability check (`SmbService.is_stable`): skip unstable files (do not touch DB / downstream).
4. “Claim” processing in DB (idempotency guard).
5. Submit to FOI extraction (upload file) and map response:
   - extraction success → submit to ITM → write DB success
   - extraction failure → write DB failure → notify IQube
   - ITM failure → write DB failure → notify IQube
6. Archive runs asynchronously in background:
   - scan-candidates (“older versions”) moved to archive
   - DB housekeeping: archive `success/ops_*` files not yet archived, then write `archive_succeeded`

## Test execution model

All integration tests:
- use real SMB share + real Postgres
- call a *running* coordinator instance via HTTP (`IT_COORDINATOR_BASE_URL`)
- start fake downstream services via pytest:
  - fake ITM (`http://127.0.0.1:18081`)
  - fake IQube (`http://127.0.0.1:18082`)
- optional fake FOI (`http://127.0.0.1:18083`) for *forcing* FOI failures

## Environment flags

- `IT_KEEP_ARTIFACTS=1`: keep SMB/DB artifacts for debugging.
- `IT_RUN_FOI_FAILURE_TESTS=1`: enable tests that require coordinator to point to fake FOI.

## Test case matrix

### A) Happy path

- **A1: FOI success → ITM success → DB `success` → archive**
  - Expected: 1 ITM submission; 0 IQube notifications; DB contains `success`; file moved to archive (async housekeeping).
  - Test: `tests/integration/test_happy_path_integration.py::test_happy_path_seed_file_calls_itm_and_archives`
  - Notes: uses the seed file under `tests/integration/files/invest@det.com/`.

### B) Scan + newest-selection (timestamp versions)

These validate that we only process the newest version and archive older versions, based on `strip_ts_basename()` grouping and basename sort.

- **B1: 14-digit timestamps (YYYYMMDDHHMMSS)**
  - Expected: older file is archived; newest file creates DB record; older file does **not** create DB record.
  - Test: `tests/integration/test_coordinator_run_integration.py::test_case1_timstamp_versions_archive_older_only_process_newest`

- **B2: Multiple remitters + newest selection**
  - Expected: for each remitter, older version archived; newest version creates DB record.
  - Test: `tests/integration/test_coordinator_run_seed_files_integration.py::test_seed_files_multi_remitters_timestamp`

- **B3: 8-digit timestamps (YYYYMMDD)**
  - Expected: older file archived; newest file creates DB record; older file does **not** create DB record.
  - Test: `tests/integration/test_timestamp_variants_integration.py::test_timestamp_8_digits_versions_archive_older_only_process_newest`

- **B4: Mixed 8-digit + 14-digit timestamps**
  - Expected: the 14-digit version is treated as newer and processed; 8-digit older version archived.
  - Test: `tests/integration/test_timestamp_variants_integration.py::test_timestamp_mixed_8_and_14_digits_archive_older_process_newest`

- **B5: Unsupported timestamp formats**
  - Current behavior: formats like `YYYYMMDDTHHMMSS` (or ms suffix) are **not** grouped; each file is treated as a separate base and can be processed independently (potential duplicate processing if the “same logical file” is produced with different naming conventions).
  - Test: `tests/integration/test_timestamp_variants_integration.py::test_timestamp_unsupported_format_t_separator_creates_separate_records`

### C) Policy A (SMB stability / incomplete upload protection)

- **C1: Newly written file is unstable → skipped**
  - Expected: file remains in source; 0 downstream calls; no DB record; no archive move.
  - Test: `tests/integration/test_policy_a_unstable_file_integration.py::test_unstable_file_should_be_skipped`

- **C2: Slow upload (partially written) → skipped until upload completes**
  - Expected (1st run during upload): no DB/downstream/archive.
  - Expected (2nd run after upload complete): file is processed (DB record and/or downstream call).
  - Test: `tests/integration/test_coordinator_run_slow_upload_integration.py::test_slow_upload_should_be_skipped_until_complete`

### D) Temp / partial file name filtering during scan

- **D1: Temp-like files are ignored by `list_files`**
  - Expected: temp files remain in source; no DB record.
  - Test: `tests/integration/test_temp_files_ignored_integration.py::test_temp_files_should_be_ignored_by_scan`

### E) FOI extraction failure mapping (requires fake FOI)

**Prereqs**
- Start coordinator with `FOI_API_URL=http://127.0.0.1:18083/extract/{remitter}` and `ENV=local`
- Run pytest with `IT_RUN_FOI_FAILURE_TESTS=1`

Expected common behavior for extraction failures:
- DB records an extraction failure status
- IQube is notified once
- ITM is not called
- File remains in source and is not archived

Cases covered:
- **E1: Invalid password → `extraction_file_password_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_invalid_password_maps_to_password_failed`

- **E2: Non-dict JSON / parse issues → `extraction_service_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_service_failure_maps_to_service_failed`

- **E3: FOI `failed[]` reason “no matched template” → `extraction_file_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_no_template_match_maps_to_extraction_file_failed`

- **E4: FOI `failed[]` reason “data format error” → `extraction_file_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_data_format_error_maps_to_extraction_file_failed`

- **E5: FOI HTTP 422 → `extraction_file_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_http_422_maps_to_extraction_file_failed`

- **E6: FOI HTTP 400 → `extraction_file_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_http_400_maps_to_extraction_file_failed`

- **E7: FOI missing `result` → `extraction_service_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_missing_result_maps_to_service_failed`

- **E8: FOI empty `result` → `extraction_service_failed`**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_empty_result_maps_to_service_failed`

- **E9: Idempotency after extraction failure (repeat run must not reprocess)**
  - Test: `tests/integration/test_foi_failure_integration.py::test_foi_invalid_password_is_not_reprocessed_on_second_run`

### F) ITM failure + idempotency (file must not be reprocessed)

- **F1: ITM returns `status=failed`**
  - Expected: DB writes `itm_failed`; IQube notified; file remains in source (not archived); repeated runs do not call downstream again and do not add DB rows.
  - Test: `tests/integration/test_itm_failure_and_idempotency_integration.py::test_itm_failed_file_is_not_archived_and_not_reprocessed`

## Gaps / TODO test cases (not implemented yet)

These require fault injection against real SMB/PG or coordinator internals, so they are best covered by:
- unit tests (mock SMB client / DB session), or
- a coordinator subprocess mode dedicated for integration fault injection.

Suggested cases:
- SMB scan failure (`SmbService.list_files` raises) → run returns fatal error and IQube notified once.
- SMB download/MD5 failure (file disappears mid-run / permission error) → process_one exception handling and DB/IQube behavior.
- FOI request timeout / connection reset → maps to `extraction_service_failed`.
- Archive failures (SMB move fails) → background error logged; run API still returns successfully; housekeeping retries.

