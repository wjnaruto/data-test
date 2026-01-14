# Integration Tests (Real SMB + Real Postgres)

These tests call a running coordinator instance via HTTP and use real SMB + real Postgres.

## Test case catalog
- See `tests/integration/TEST_CASES.md` for a categorized list of happy-path vs failure/exception scenarios.

## Prerequisites
- Start Postgres and ensure `DATABASE_URL` in `.env.it` is reachable.
- Provide a dedicated SMB folder for tests (`SMB_UNC_PATH` + `SMB_ARCHIVE_SUBPATH`) to avoid interference from non-test files.
- Start coordinator locally before running pytest.

## Required `.env.it`
- `DATABASE_URL`
- `SMB_UNC_PATH`
- `SMB_ARCHIVE_SUBPATH`
- `IT_COORDINATOR_BASE_URL` (e.g. `http://localhost:8080`)
- `IT_SMB_USERNAME`
- `IT_SMB_PASSWORD`

## Fake downstream services (recommended)
Pytest starts fake ITM + fake IQube by default:
- fake ITM: `http://127.0.0.1:18081`
- fake IQube: `http://127.0.0.1:18082`

To make assertions meaningful, start coordinator with:
- `ITM_API_URL=http://127.0.0.1:18081/itm`
- `IQUBE_API_URL=http://127.0.0.1:18082/notify`

## Optional: FOI failure tests (fake FOI)
Some tests require forcing FOI responses.

Pytest can start a fake FOI server at `http://127.0.0.1:18083`, but your coordinator must point to it:
- `FOI_API_URL=http://127.0.0.1:18083/extract/{remitter}`
- `ENV=local` (so the ID token manager won’t call Google for localhost)

Run FOI failure tests with:
- `IT_RUN_FOI_FAILURE_TESTS=1`

## Debugging
- Keep SMB/DB artifacts: set `IT_KEEP_ARTIFACTS=1`
