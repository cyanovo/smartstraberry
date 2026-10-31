"""Department-scoped field workflow records and atomic state transitions."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from yuxi.repositories.album_repository import serialize
from yuxi.storage.postgres.manager import pg_manager


class Base(DeclarativeBase):
    pass


class FieldRecord(Base):
    __tablename__ = "field_work_records"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    department_id: Mapped[int] = mapped_column(Integer, index=True)
    owner_uid: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FieldWorkRepository:
    async def initialize(self, validate=False):
        async with pg_manager.async_engine.begin() as connection:
            if validate:
                await connection.execute(select(FieldRecord).limit(0))
            else:
                await connection.run_sync(Base.metadata.create_all)

    async def create(self, kind, name, user, *, parent_id="", status="ready", data=None):
        async with pg_manager.get_async_session_context() as session:
            if kind == "detection":
                from yuxi.repositories.album_repository import AlbumPhoto

                photo = await session.scalar(
                    select(AlbumPhoto)
                    .where(AlbumPhoto.id == data["photo_id"], AlbumPhoto.department_id == user.department_id)
                    .with_for_update()
                )
                if photo is None:
                    raise ValueError("原图已被删除，不能创建识别记录")
            row = FieldRecord(
                id=uuid4().hex,
                department_id=user.department_id,
                owner_uid=str(user.uid),
                kind=kind,
                name=name,
                parent_id=parent_id,
                status=status,
                data=data or {},
            )
            session.add(row)
            await session.flush()
            return serialize(row)

    async def get(self, record_id, department_id, kind=None):
        async with pg_manager.get_async_session_context() as session:
            query = select(FieldRecord).where(FieldRecord.id == record_id, FieldRecord.department_id == department_id)
            if kind:
                query = query.where(FieldRecord.kind == kind)
            row = await session.scalar(query)
            return serialize(row) if row else None

    async def list(self, kind, department_id, parent_id=None, limit=100, offset=0, status=None, owner_uid=None):
        async with pg_manager.get_async_session_context() as session:
            query = select(FieldRecord).where(FieldRecord.kind == kind, FieldRecord.department_id == department_id)
            if owner_uid is not None:
                query = query.where(FieldRecord.owner_uid == str(owner_uid))
            if parent_id is not None:
                query = query.where(FieldRecord.parent_id == parent_id)
            if status is not None:
                query = query.where(FieldRecord.status == status)
            rows = await session.scalars(
                query.order_by(FieldRecord.created_at.desc(), FieldRecord.id).limit(limit).offset(offset)
            )
            return [serialize(row) for row in rows]

    async def change(self, record_id, department_id, *, status, data=None, expected=None):
        values = {"status": status, "updated_at": datetime.now(UTC)}
        if data is not None:
            values["data"] = data
        async with pg_manager.get_async_session_context() as session:
            query = update(FieldRecord).where(FieldRecord.id == record_id, FieldRecord.department_id == department_id)
            if expected is not None:
                query = query.where(FieldRecord.status == expected)
            result = await session.execute(query.values(**values))
            return result.rowcount == 1

    async def recover(self):
        # Restart never silently resumes camera access or retries physical commands.
        async with pg_manager.get_async_session_context() as session:
            for kind, old, new in [
                ("capture", "running", "paused"),
                ("backup", "running", "interrupted"),
                ("detection", "running", "interrupted"),
                ("model", "validating", "interrupted"),
                ("control", "sending", "unknown"),
                ("disease_care", "sending", "unknown"),
            ]:
                await session.execute(
                    update(FieldRecord)
                    .where(FieldRecord.kind == kind, FieldRecord.status == old)
                    .values(status=new, updated_at=datetime.now(UTC))
                )


field_repository = FieldWorkRepository()
