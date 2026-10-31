"""One cluster is one album; department-scoped originals cannot be assigned twice."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from yuxi.storage.postgres.manager import pg_manager


class Base(DeclarativeBase):
    pass


class ClusterAlbum(Base):
    __tablename__ = "cluster_albums"
    __table_args__ = (UniqueConstraint("department_id", "cluster_code"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    department_id: Mapped[int] = mapped_column(Integer, index=True)
    owner_uid: Mapped[str] = mapped_column(String(128))
    cluster_code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    plot: Mapped[str] = mapped_column(String(128))
    device_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AlbumPhoto(Base):
    __tablename__ = "album_photos"
    __table_args__ = (UniqueConstraint("department_id", "sha256"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    album_id: Mapped[str] = mapped_column(ForeignKey("cluster_albums.id", ondelete="RESTRICT"), index=True)
    department_id: Mapped[int] = mapped_column(Integer)
    owner_uid: Mapped[str] = mapped_column(String(128))
    filename: Mapped[str] = mapped_column(String(255))
    extension: Mapped[str] = mapped_column(String(8))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), default="upload")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def serialize(row):
    return {
        column.name: (value.isoformat() if isinstance(value, datetime) else value)
        for column in row.__table__.columns
        if (value := getattr(row, column.name)) is not None
    }


class AlbumRepository:
    async def delete_photo(self, photo_id, department_id):
        from yuxi.repositories.field_work_repository import FieldRecord

        async with pg_manager.get_async_session_context() as session:
            row = await session.scalar(select(AlbumPhoto).where(
                AlbumPhoto.id == photo_id, AlbumPhoto.department_id == department_id).with_for_update())
            if row is None:
                return False
            conditions = (
                FieldRecord.department_id == department_id,
                FieldRecord.kind == "detection",
                FieldRecord.data["photo_id"].as_string() == photo_id,
            )
            task = FieldRecord.data["task"].as_string()
            linked = await session.scalar(
                select(FieldRecord.id).where(*conditions, task.is_distinct_from("disease")).limit(1)
            )
            if linked:
                raise ValueError("图片仍关联成熟度或其他识别记录，不能删除原图及病虫害记录")
            # The photo lock also serializes detection creation; both deletions commit together.
            await session.execute(delete(FieldRecord).where(*conditions, task == "disease"))
            await session.delete(row)
            return True

    async def initialize(self, *, validate=False):
        async with pg_manager.async_engine.begin() as connection:
            if validate:
                await connection.execute(select(ClusterAlbum).limit(0))
                await connection.execute(select(AlbumPhoto).limit(0))
            else:
                await connection.run_sync(Base.metadata.create_all)

    async def create(self, **values):
        async with pg_manager.get_async_session_context() as session:
            row = ClusterAlbum(**values)
            session.add(row)
            await session.flush()
            return serialize(row)

    async def get(self, album_id, department_id):
        async with pg_manager.get_async_session_context() as session:
            row = await session.scalar(
                select(ClusterAlbum).where(ClusterAlbum.id == album_id, ClusterAlbum.department_id == department_id)
            )
            return serialize(row) if row else None

    async def list(self, department_id, limit=50, offset=0):
        async with pg_manager.get_async_session_context() as session:
            condition = ClusterAlbum.department_id == department_id
            total = await session.scalar(select(func.count()).select_from(ClusterAlbum).where(condition))
            counts = select(func.count(AlbumPhoto.id)).where(AlbumPhoto.album_id == ClusterAlbum.id).scalar_subquery()
            rows = await session.execute(
                select(ClusterAlbum, counts)
                .where(condition)
                .order_by(ClusterAlbum.created_at.desc(), ClusterAlbum.id)
                .limit(limit)
                .offset(offset)
            )
            return {"total": total, "items": [{**serialize(row), "photo_count": count} for row, count in rows]}

    async def add_photo(self, **values):
        async with pg_manager.get_async_session_context() as session:
            row = AlbumPhoto(**values)
            session.add(row)
            await session.flush()
            return serialize(row)

    async def photos(self, album_id, department_id, limit=24, offset=0):
        async with pg_manager.get_async_session_context() as session:
            conditions = (AlbumPhoto.album_id == album_id, AlbumPhoto.department_id == department_id)
            total = await session.scalar(select(func.count()).select_from(AlbumPhoto).where(*conditions))
            rows = await session.scalars(
                select(AlbumPhoto)
                .where(*conditions)
                .order_by(AlbumPhoto.captured_at.desc(), AlbumPhoto.id)
                .limit(limit)
                .offset(offset)
            )
            return {"total": total, "items": [serialize(row) for row in rows]}

    async def photo(self, photo_id, department_id):
        async with pg_manager.get_async_session_context() as session:
            row = await session.scalar(
                select(AlbumPhoto).where(AlbumPhoto.id == photo_id, AlbumPhoto.department_id == department_id)
            )
            return serialize(row) if row else None


album_repository = AlbumRepository()
