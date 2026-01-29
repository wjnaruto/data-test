from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import func, desc, select, exists, and_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import aliased

from db.models import ControlRecord, generate_record_id
from misc.config import settings
from misc.constants import Status
from logs.logging_utils import log_event
from models.domain.file import FileDetailResponse


class Recorder:
    def __init__(self, session, instance_id: Optional[str] = None):
        self.session = session
        self.instance_id = instance_id or settings.INSTANCE_ID

    async def try_claim_processing(
        self,
        *,
        file_name: str,
        base_name: str,
        md5: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        stmt = (
            insert(ControlRecord)
            .values(
                id=generate_record_id(),
                file_name=file_name,
                base_name=base_name,
                content_md5=md5,
                status=Status.PROCESSING,
                message="claimed",
                instance_id=self.instance_id,
                correlation_id=correlation_id,
                created_at=datetime.utcnow(),
            )
            .on_conflict_do_nothing(
                index_elements=["base_name", "content_md5"],
                index_where=text("status = 'processing'"),
            )
            .returning(ControlRecord.id)
        )
        try:
            res = await self.session.execute(stmt)
            return res.scalar() is not None
        except sa_exc.IntegrityError:
            return False

    async def insert_status(
        self,
        *,
        file_name: str,
        base_name: str,
        md5: str,
        status: str,
        message: Optional[str] = None,
        attempt_no: int = 0,
        correlation_id: Optional[str] = None,
    ) -> str:
        rec = ControlRecord(
            file_name=file_name,
            base_name=base_name,
            content_md5=md5,
            status=status,
            message=message,
            attempt_no=attempt_no,
            instance_id=self.instance_id,
            correlation_id=correlation_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(rec)
        return rec.id

    async def list_unarchived_files(self, *, limit: int | None = None) -> list[ControlRecord]:
        latest = (
            select(ControlRecord)
            .distinct(ControlRecord.file_name, ControlRecord.content_md5)
            .order_by(ControlRecord.file_name,
                      ControlRecord.content_md5,
                      ControlRecord.created_at.desc()
            ).subquery("latest")
        )
        cr = aliased(ControlRecord, latest)

        arch_exists = exists(
            select(1).where(
                and_(
                    ControlRecord.file_name == cr.file_name,
                    ControlRecord.content_md5 == cr.content_md5,
                    ControlRecord.status == Status.ARCHIVE_SUCCEEDED
                )
            )
        )

        stmt = (
            select(cr)
            .where(
                cr.status.in_([
                    Status.SUCCESS,
                    Status.OPS_CLOSED,
                    Status.OPS_REJECTED
                ])
            )
            .where(~arch_exists)
        )

        if limit is not None:
            stmt = stmt.order_by(cr.created_at.asc()).limit(limit)

        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_itm_internal_failed_files(self, *, limit: int | None = None) -> list[ControlRecord]:
        """
        Return the latest record for each (file_name, content_md5) whose latest status is ITM_INTERNAL_FAILED.
        These are candidates for postprocess retry.
        """
        latest = (
            select(ControlRecord)
            .distinct(ControlRecord.file_name, ControlRecord.content_md5)
            .order_by(
                ControlRecord.file_name,
                ControlRecord.content_md5,
                ControlRecord.created_at.desc(),
            )
            .subquery("latest_itm_internal_failed")
        )
        cr = aliased(ControlRecord, latest)

        stmt = select(cr).where(cr.status == Status.ITM_INTERNAL_FAILED)
        if limit is not None:
            stmt = stmt.order_by(cr.created_at.asc()).limit(limit)

        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_file_by_id(self, record_id: str) -> Optional[ControlRecord]:
        stmt = (
            select(ControlRecord).where(ControlRecord.id == record_id)
            .order_by(desc(ControlRecord.created_at)).limit(1)
        )
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return None
        return row[0]
    

    async def reject_file_and_archive_record(
        self,
        file_name: str,
        base_name: str,
        md5_value: str,
        reason: str,
        username: str,
    ) -> str:
        rec_id = await self.insert_status(
            file_name=file_name,
            base_name=base_name,
            md5=md5_value,
            status=Status.OPS_REJECTED,
            message=reason or "rejected_by_user",
            correlation_id=username
        )
        log_event(event="REJECT_FILE_DB_COMMIT", file=file_name, message=f"Insert Reject Record: MDS: {md5_value}")
        return rec_id

    async def get_file_detail_by_id(self, id: str) -> Optional[FileDetailResponse]:
        """
        Query file details using unique ID
        """
        stmt = (
            select(
                ControlRecord.id,
                ControlRecord.file_name,
                ControlRecord.base_name,
                ControlRecord.status,
                ControlRecord.message,
                ControlRecord.created_at,
                ControlRecord.content_md5
            )
            .where(ControlRecord.id == id)
            .order_by(desc(ControlRecord.created_at))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            log_event(event="GET_FILE_NOT_FOUND", file=id, level="error", message="File not found (recorder)")
            return None

        log_event(event="GET_FILE_DB_OK", file=id, message="File details successfully retrieved (recorder)")
        return FileDetailResponse(
            id=row.id,
            file_name=row.file_name,
            base_name=row.base_name,
            status=row.status,
            reason=row.message,
            occurred_at=row.created_at,
            md5=row.content_md5
        )
