from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yuxi.repositories.album_repository import AlbumPhoto, Base, album_repository
from yuxi.repositories.field_work_repository import Base as FieldBase
from yuxi.repositories.field_work_repository import FieldRecord
from yuxi.storage.postgres.manager import pg_manager


@pytest.fixture
async def database(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(FieldBase.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def session_context():
        async with factory() as session, session.begin():
            yield session

    monkeypatch.setattr(pg_manager, "get_async_session_context", session_context)
    async with session_context() as session:
        session.add(AlbumPhoto(
            id="photo", album_id="album", department_id=1, owner_uid="u",
            filename="fruit.png", extension="png", sha256="abc", size=10,
            width=1, height=1, captured_at=datetime.now(UTC),
        ))
        for record_id, department, photo, task, kind, status in [
            ("d1", 1, "photo", "disease", "detection", "ready"),
            ("d2", 1, "photo", "disease", "detection", "failed"),
            ("other-photo", 1, "other", "disease", "detection", "ready"),
            ("other-department", 2, "photo", "disease", "detection", "ready"),
            ("other-kind", 1, "photo", "disease", "analysis", "ready"),
        ]:
            session.add(FieldRecord(
                id=record_id, department_id=department, owner_uid="u", kind=kind,
                name=record_id, status=status, data={"photo_id": photo, "task": task},
            ))
    yield session_context
    await engine.dispose()


async def test_delete_cascades_only_linked_disease_records(database):
    assert await album_repository.delete_photo("photo", 1)
    async with database() as session:
        assert await session.get(AlbumPhoto, "photo") is None
        assert set(await session.scalars(select(FieldRecord.id))) == {
            "other-photo", "other-department", "other-kind",
        }


async def test_wrong_department_and_missing_photo_do_not_delete(database):
    assert not await album_repository.delete_photo("photo", 2)
    assert not await album_repository.delete_photo("missing", 1)
    async with database() as session:
        assert await session.get(AlbumPhoto, "photo") is not None
        assert len(list(await session.scalars(select(FieldRecord.id)))) == 5


@pytest.mark.parametrize("task", ["maturity", None])
async def test_other_detection_keeps_photo_and_all_disease_records(database, task):
    async with database() as session:
        session.add(FieldRecord(
            id="protected", department_id=1, owner_uid="u", kind="detection",
            name="protected", data={"photo_id": "photo", "task": task},
        ))
    with pytest.raises(ValueError):
        await album_repository.delete_photo("photo", 1)
    async with database() as session:
        assert await session.get(AlbumPhoto, "photo") is not None
        assert len(list(await session.scalars(select(FieldRecord.id)))) == 6


async def test_database_failure_rolls_back_disease_deletion(database, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    async def fail_delete(self, row):
        raise RuntimeError("delete failed")

    monkeypatch.setattr(AsyncSession, "delete", fail_delete)
    with pytest.raises(RuntimeError, match="delete failed"):
        await album_repository.delete_photo("photo", 1)
    async with database() as session:
        assert await session.get(AlbumPhoto, "photo") is not None
        assert len(list(await session.scalars(select(FieldRecord.id)))) == 5
