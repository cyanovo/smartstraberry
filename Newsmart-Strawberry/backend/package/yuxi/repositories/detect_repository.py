"""检测记录数据持久化"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase

from yuxi.detect.schemas import DetectResult, Detection
from yuxi.storage.postgres.manager import pg_manager
from yuxi.utils import logger


class Base(DeclarativeBase):
    pass


class DetectRecord(Base):
    """检测记录表"""

    __tablename__ = "detect_records"

    id = Column(String(32), primary_key=True)
    zone = Column(String(10), nullable=False, index=True)
    camera_id = Column(Integer, default=0)
    total_count = Column(Integer, nullable=False)
    ripe_count = Column(Integer, nullable=False)
    half_ripe_count = Column(Integer, nullable=False)
    unripe_count = Column(Integer, nullable=False)
    maturity_ratio = Column(Float, nullable=False)
    confidence_threshold = Column(Float, default=0.5)
    detections_json = Column(Text, default="[]")
    recommendation = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now, index=True)


class DetectRepository:
    """检测记录仓储"""

    async def init_table(self):
        """初始化表结构（如不存在则创建）"""
        try:
            async with pg_manager.get_async_session_context() as session:
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS detect_records (
                        id VARCHAR(32) PRIMARY KEY,
                        zone VARCHAR(10) NOT NULL,
                        camera_id INT DEFAULT 0,
                        total_count INT NOT NULL,
                        ripe_count INT NOT NULL,
                        half_ripe_count INT NOT NULL,
                        unripe_count INT NOT NULL,
                        maturity_ratio FLOAT NOT NULL,
                        confidence_threshold FLOAT DEFAULT 0.5,
                        detections_json TEXT DEFAULT '[]',
                        recommendation TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_detect_zone ON detect_records(zone)
                """))
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_detect_created ON detect_records(created_at DESC)
                """))
                # commit is handled by the context manager
                logger.info("检测记录表初始化完成")
        except Exception as e:
            logger.error(f"检测记录表初始化失败: {e}")

    async def save_record(self, result: DetectResult) -> None:
        """保存检测记录"""
        try:
            async with pg_manager.get_async_session_context() as session:
                await session.execute(
                    text("""
                        INSERT INTO detect_records
                        (id, zone, camera_id, total_count, ripe_count, half_ripe_count,
                         unripe_count, maturity_ratio, confidence_threshold,
                         detections_json, recommendation, created_at)
                        VALUES
                        (:id, :zone, :camera_id, :total_count, :ripe_count, :half_ripe_count,
                         :unripe_count, :maturity_ratio, :confidence_threshold,
                         :detections_json, :recommendation, :created_at)
                    """),
                    {
                        "id": result.id,
                        "zone": result.zone,
                        "camera_id": result.camera_id,
                        "total_count": result.total_count,
                        "ripe_count": result.ripe_count,
                        "half_ripe_count": result.half_ripe_count,
                        "unripe_count": result.unripe_count,
                        "maturity_ratio": result.maturity_ratio,
                        "confidence_threshold": result.confidence_threshold,
                        "detections_json": json.dumps(
                            [d.model_dump() for d in result.detections],
                            ensure_ascii=False,
                        ),
                        "recommendation": result.recommendation,
                        "created_at": result.created_at,
                    },
                )
                logger.info(f"检测记录已保存: {result.id}")
        except Exception as e:
            logger.error(f"保存检测记录失败: {e}")
            raise

    async def get_records(
        self, zone: str | None = None, limit: int = 20
    ) -> list[DetectResult]:
        """查询检测历史"""
        try:
            async with pg_manager.get_async_session_context() as session:
                query = "SELECT * FROM detect_records"
                params: dict = {"limit": limit}

                if zone:
                    query += " WHERE zone = :zone"
                    params["zone"] = zone

                query += " ORDER BY created_at DESC LIMIT :limit"

                result = await session.execute(text(query), params)
                rows = result.mappings().all()

                return [self._row_to_result(row) for row in rows]
        except Exception as e:
            logger.error(f"查询检测记录失败: {e}")
            return []

    async def get_stats(self) -> dict:
        """获取各区域成熟度统计"""
        try:
            async with pg_manager.get_async_session_context() as session:
                result = await session.execute(text("""
                    SELECT
                        zone,
                        COUNT(*) as scan_count,
                        ROUND(AVG(maturity_ratio), 2) as avg_maturity,
                        SUM(total_count) as total_fruits,
                        SUM(ripe_count) as ripe_fruits,
                        MAX(created_at) as last_scan
                    FROM detect_records
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    GROUP BY zone
                    ORDER BY zone
                """))

                rows = result.mappings().all()
                stats = {}
                for row in rows:
                    stats[row["zone"]] = {
                        "scan_count": row["scan_count"],
                        "avg_maturity": float(row["avg_maturity"] or 0),
                        "total_fruits": row["total_fruits"],
                        "ripe_fruits": row["ripe_fruits"],
                        "last_scan": row["last_scan"].isoformat() if row["last_scan"] else None,
                    }
                return stats
        except Exception as e:
            logger.error(f"获取检测统计失败: {e}")
            return {}

    @staticmethod
    def _row_to_result(row) -> DetectResult:
        """将数据库行转换为 DetectResult"""
        detections_data = json.loads(row["detections_json"] or "[]")
        detections = [Detection(**d) for d in detections_data]

        return DetectResult(
            id=row["id"],
            zone=row["zone"],
            camera_id=row["camera_id"],
            total_count=row["total_count"],
            ripe_count=row["ripe_count"],
            half_ripe_count=row["half_ripe_count"],
            unripe_count=row["unripe_count"],
            maturity_ratio=float(row["maturity_ratio"]),
            confidence_threshold=float(row["confidence_threshold"]),
            detections=detections,
            recommendation=row["recommendation"] or "",
            created_at=row["created_at"],
        )


# 模块级单例
detect_repository = DetectRepository()
