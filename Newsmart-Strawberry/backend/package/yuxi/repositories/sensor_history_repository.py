"""Append-only sensor samples; Redis remains the latest-value cache."""

from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Index, String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from yuxi.storage.postgres.manager import pg_manager


class Base(DeclarativeBase):
    pass


class SensorSample(Base):
    __tablename__ = "sensor_samples"
    __table_args__ = (Index("ix_sensor_samples_device_time", "device_id", "sampled_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)


class SensorHistoryRepository:
    async def initialize(self):
        async with pg_manager.async_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def append(self, *, device_id: str, kind: str, sampled_at: datetime, values: dict):
        sample = SensorSample(
            id=uuid4().hex,
            device_id=device_id,
            kind=kind,
            sampled_at=sampled_at,
            received_at=datetime.now(UTC),
            values=values,
        )
        async with pg_manager.get_async_session_context() as session:
            session.add(sample)

    async def query(self, *, device_id=None, kind=None, start=None, end=None, limit=100, offset=0):
        conditions = []
        if device_id:
            conditions.append(SensorSample.device_id == device_id)
        if kind:
            conditions.append(SensorSample.kind == kind)
        if start:
            conditions.append(SensorSample.sampled_at >= start)
        if end:
            conditions.append(SensorSample.sampled_at <= end)
        async with pg_manager.get_async_session_context() as session:
            total = await session.scalar(select(func.count()).select_from(SensorSample).where(*conditions))
            rows = await session.scalars(
                select(SensorSample)
                .where(*conditions)
                .order_by(SensorSample.sampled_at.desc(), SensorSample.id.desc())
                .offset(offset)
                .limit(limit)
            )
            return {
                "total": total,
                "items": [
                    {
                        "id": row.id,
                        "device_id": row.device_id,
                        "kind": row.kind,
                        "sampled_at": row.sampled_at.isoformat(),
                        "received_at": row.received_at.isoformat(),
                        "values": row.values,
                    }
                    for row in rows
                ],
            }

    async def devices(self):
        async with pg_manager.get_async_session_context() as session:
            rows = await session.scalars(select(SensorSample.device_id).distinct().order_by(SensorSample.device_id))
            return list(rows)


sensor_history_repository = SensorHistoryRepository()
