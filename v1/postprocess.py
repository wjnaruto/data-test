import asyncio
import json
import ntpath
from typing import Iterable, List

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from misc.config import settings
from misc.constants import Events, Status, FailureKind
from db.db import session_manager
from db.recorder import Recorder
from logs.logging_utils import log_event
from services.smb_service import SmbService
from services.extraction_service import ExtractionService
from clients.itm import ITMClient
from clients.iqube import IQubeClient
import misc.utils as utils


class PostprocessService:
    def __init__(self, smb: SmbService):
        self.smb = smb

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRY_COUNT),
        wait=wait_exponential(multiplier=settings.RETRY_BASE_SECONDS, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def archive(self, files_to_archive: Iterable[str] | None = None) -> bool:
        """
        Archive source files in two categories:
        1) Scan-derived candidates (typically "old" files we decided not to process) - no DB record expected.
        2) DB housekeeping candidates (processed/closed/rejected but not yet archived) - archive and then write DB status.
        """
        ok_itm = await self._retry_itm_internal_failures()
        ok_scan = await self._archive_scan_candidates(files_to_archive or [])
        ok_housekeeping = await self._archive_db_housekeeping_candidates()
        return ok_itm and ok_scan and ok_housekeeping

    async def _retry_itm_internal_failures(self) -> bool:
        """
        Retry files whose latest status is ITM_INTERNAL_FAILED.

        Plan A: re-run FOI extraction using filename-based API, then resubmit to ITM.
        """
        async with session_manager() as session:
            rec = Recorder(session)
            candidates = await rec.list_itm_internal_failed_files(limit=settings.ARCHIVE_BATCH_SIZE)

        if not candidates:
            return True

        extraction_svc = ExtractionService()
        itm = ITMClient()
        iqube = IQubeClient()
        try:
            for r in candidates:
                path = r.file_name
                base = r.base_name
                md5 = r.content_md5
                remitter = utils.extract_remitter(path)
                filename = ntpath.basename(path)

                result = await extraction_svc.extract_with_file_name(filename=filename, remitter=remitter)
                if not result.ok:
                    # Best-effort: record extraction failure. This should be rare because candidates previously
                    # had extraction succeed; avoid spamming IQube here and rely on normal run alerts.
                    async with session_manager() as session:
                        recorder = Recorder(session)
                        async with session.begin():
                            await recorder.insert_status(
                                file_name=path,
                                base_name=base,
                                md5=md5,
                                status=Status.EXTRACTION_SERVICE_FAILED
                                if result.kind == FailureKind.SERVICE
                                else Status.EXTRACTION_FILE_FAILED,
                                message=json.dumps(result.rows or result.message or "")[:500],
                                correlation_id=r.correlation_id,
                            )
                    continue

                ok, msg, retryable_internal = await itm.submit(result.rows[0], remitter, path)
                if ok:
                    async with session_manager() as session:
                        recorder = Recorder(session)
                        async with session.begin():
                            await recorder.insert_status(
                                file_name=path,
                                base_name=base,
                                md5=md5,
                                status=Status.SUCCESS,
                                message="SUCCESS",
                                correlation_id=r.correlation_id,
                            )
                    continue

                status = Status.ITM_INTERNAL_FAILED if retryable_internal else Status.ITM_FAILED
                rid = None
                async with session_manager() as session:
                    recorder = Recorder(session)
                    async with session.begin():
                        rid = await recorder.insert_status(
                            file_name=path,
                            base_name=base,
                            md5=md5,
                            status=status,
                            message=(msg or "itm_failed")[:500],
                            correlation_id=r.correlation_id,
                        )

                if not retryable_internal:
                    try:
                        await iqube.notify_file_error(path, reason=Status.ITM_FAILED, record_id=rid)
                    except Exception as e:
                        log_event("IQUBE_NOTIFY_ERROR", level="error", file=path, message=str(e))

            return True
        finally:
            await extraction_svc.close()
            await itm.aclose()
            await iqube.close()

    async def _archive_scan_candidates(self, files_to_archive: Iterable[str] | None = None) -> bool:
        names = list(dict.fromkeys([x for x in (files_to_archive or []) if x]))
        if not names:
            log_event(Events.ARCHIVE_SOURCE_OK, message="No files to archive")
            return True

        failed = 0
        for file_name in names:
            ok, msg = await asyncio.to_thread(self.smb.archive_source, file_name)
            if not ok:
                failed += 1
                log_event(Events.ARCHIVE_SOURCE_FAILED, file=file_name, message=f"archive scan-candidate failed: {msg}")

        if failed:
            log_event(Events.ARCHIVE_SOURCE_FAILED, message=f"archive failed: {failed}")
            return False
        log_event(Events.ARCHIVE_SOURCE_OK, message=f"archive done")
        return True

    async def _archive_db_housekeeping_candidates(self) -> bool:
        async with session_manager() as session:
            rec = Recorder(session)
            db_candidates = await rec.list_unarchived_files(limit=settings.ARCHIVE_BATCH_SIZE)

        if not db_candidates:
            log_event(Events.ARCHIVE_SOURCE_OK, message="No files to archive")
            return True

        failed = 0
        succeeded = []

        for rec in db_candidates:
            ok, msg = await asyncio.to_thread(self.smb.archive_source, rec.file_name)
            if not ok:
                failed += 1
                log_event(Events.ARCHIVE_SOURCE_FAILED, file=rec.file_name, message=f"archive failed: {msg}")
                continue
            succeeded.append(rec)

        if succeeded:
            async with session_manager() as session:
                recorder = Recorder(session)
                async with session.begin():
                    for rec in succeeded:
                        await recorder.insert_status(
                            file_name=rec.file_name,
                            base_name=rec.base_name,
                            md5=rec.content_md5,
                            status=Status.ARCHIVE_SUCCEEDED,
                            message=f"archive succeeded",
                            correlation_id=rec.correlation_id
                        )

        total = len(succeeded)
        if failed:
            log_event(Events.ARCHIVE_SOURCE_FAILED, message=f"archive failed: {failed}")
            return False

        log_event(Events.ARCHIVE_SOURCE_OK, message=f"archive done for {total} files (all succeeded)")

        return True
