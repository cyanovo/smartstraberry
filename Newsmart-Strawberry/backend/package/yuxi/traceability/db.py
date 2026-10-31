"""
番茄溯源系统 — 数据库层

完整溯源链路设计：
种子来源 → 地块规划 → 播种 → 田间管理(浇水/施肥/打药) → 生长监测(温湿度)
    → 采摘 → 质检 → 包装(生成溯源码) → 销售 → 消费者扫码查询

实体关系：
地块(Plot) ──┐
              ├──▶ 种植批次(Batch) ──▶ 农事记录(Activity)
种子(Seed) ──┘        │                    环境数据(Environment)
                      │                    采摘记录(Harvest)
                      ▼                    质检记录(Inspection)
              包装记录(Package) ──▶ 溯源码(TraceCode) ──▶ 消费者查询
"""

import json
import os
import sqlite3
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Docker 卷路径：/app/saves 对应 docker/volumes/greenhouse
_SAVES_DIR = (
    Path("/app/saves")
    if Path("/app/saves").exists()
    else Path(__file__).resolve().parent.parent.parent.parent / "docker" / "volumes" / "greenhouse"
)
_SAVES_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _SAVES_DIR / ".tomato_trace.db"
TRACE_DATABASE_BACKEND = os.getenv("TRACE_DATABASE_BACKEND", "sqlite").strip().lower()
TRACE_DATABASE_SCHEMA_MODE = os.getenv("TRACE_DATABASE_SCHEMA_MODE", "migrate").strip().lower()


class _PostgresCursor:
    """Keep the small sqlite-style query surface used by this legacy module."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query: str, params=None):
        self._cursor.execute(query.replace("?", "%s"), params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class _PostgresConnection:
    def __init__(self, conninfo: str):
        import psycopg
        from psycopg.rows import dict_row

        self._conn = psycopg.connect(conninfo, row_factory=dict_row, connect_timeout=5)
        self._conn.execute("SET search_path TO traceability, public")

    def cursor(self) -> _PostgresCursor:
        return _PostgresCursor(self._conn.cursor())

    def execute(self, query: str, params=None) -> _PostgresCursor:
        return self.cursor().execute(query, params)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


# ══════════════════════════════════════════════════════════════════════
#  Pydantic 数据模型
# ══════════════════════════════════════════════════════════════════════

# ── 地块 ──────────────────────────────────────────────────────────


class PlotCreate(BaseModel):
    name: str = Field(..., description="地块名称，如 3号大棚")
    location: str = Field(..., description="位置描述")
    area_mu: Optional[float] = Field(None, description="面积（亩）")
    soil_type: Optional[str] = Field(None, description="土壤类型")
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    note: str = ""


class PlotUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    area_mu: Optional[float] = None
    soil_type: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    note: Optional[str] = None


class Plot(BaseModel):
    id: str
    name: str
    location: str
    area_mu: Optional[float] = None
    soil_type: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    note: str = ""
    created_at: str


# ── 种子 ──────────────────────────────────────────────────────────


class SeedCreate(BaseModel):
    variety: str = Field(..., description="品种名称")
    supplier: str = Field("", description="供应商")
    batch_no: str = Field("", description="种子批次号")
    cert_info: str = Field("", description="认证信息")
    note: str = ""


class SeedUpdate(BaseModel):
    variety: Optional[str] = None
    supplier: Optional[str] = None
    batch_no: Optional[str] = None
    cert_info: Optional[str] = None
    note: Optional[str] = None


class Seed(BaseModel):
    id: str
    variety: str
    supplier: str
    batch_no: str
    cert_info: str
    note: str = ""
    created_at: str


# ── 种植批次（溯源核心） ─────────────────────────────────────────


class BatchCreate(BaseModel):
    batch_code: str = Field(..., description="批次编号，如 BATCH-2024-001")
    plot_id: str = Field(..., description="地块ID")
    seed_id: str = Field(..., description="种子ID")
    plant_date: str = Field(..., description="种植日期 ISO 格式")
    expected_harvest_date: Optional[str] = None
    planting_method: str = Field("", description="种植方式")
    note: str = ""


class BatchUpdate(BaseModel):
    plot_id: Optional[str] = None
    seed_id: Optional[str] = None
    plant_date: Optional[str] = None
    expected_harvest_date: Optional[str] = None
    planting_method: Optional[str] = None
    status: Optional[str] = None  # growing/harvested/packaged/sold
    note: Optional[str] = None


class Batch(BaseModel):
    id: str
    batch_code: str
    plot_id: str
    seed_id: str
    plant_date: Optional[str] = None
    expected_harvest_date: Optional[str] = None
    planting_method: str = ""
    status: str = "growing"  # growing/harvested/packaged/sold
    note: str = ""
    created_at: str
    updated_at: str
    # 关联数据（查询时填充）
    plot: Optional[Plot] = None
    seed: Optional[Seed] = None
    activities: List[Dict[str, Any]] = []
    environments: List[Dict[str, Any]] = []
    harvests: List[Dict[str, Any]] = []
    inspections: List[Dict[str, Any]] = []
    packages: List[Dict[str, Any]] = []


# ── 农事操作 ──────────────────────────────────────────────────────


class ActivityCreate(BaseModel):
    batch_id: str
    datetime: str = Field(..., description="操作时间")
    type: str = Field(..., description="类型：浇水/施肥/打药/除草/其他")
    detail: str = Field("", description="具体操作内容")
    materials: str = Field("", description="使用物料，如 复合肥 5kg")
    operator: str = ""


class Activity(BaseModel):
    id: str
    batch_id: str
    datetime: str
    type: str
    detail: str
    materials: str
    operator: str
    created_at: str


# ── 环境数据 ──────────────────────────────────────────────────────


class EnvironmentCreate(BaseModel):
    batch_id: str
    datetime: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_lux: Optional[float] = None
    soil_moisture: Optional[float] = None
    note: str = ""


class Environment(BaseModel):
    id: str
    batch_id: str
    datetime: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_lux: Optional[float] = None
    soil_moisture: Optional[float] = None
    note: str = ""
    created_at: str


# ── 采摘记录 ──────────────────────────────────────────────────────


class HarvestCreate(BaseModel):
    batch_id: str
    harvest_date: str
    yield_kg: Optional[float] = None
    grade: str = Field("", description="等级：特级/一级/二级/三级")
    operator: str = ""
    note: str = ""


class Harvest(BaseModel):
    id: str
    batch_id: str
    harvest_date: str
    yield_kg: Optional[float] = None
    grade: str
    operator: str
    note: str = ""
    created_at: str


# ── 质检记录 ──────────────────────────────────────────────────────


class InspectionCreate(BaseModel):
    batch_id: str
    inspection_type: str = Field(..., description="检测类型：农残/重金属/微生物/外观")
    result: str = Field(..., description="结果：合格/不合格")
    inspector: str = ""
    lab_name: str = Field("", description="检测机构")
    report_no: str = Field("", description="报告编号")
    detail: str = ""
    inspect_date: str = ""


class Inspection(BaseModel):
    id: str
    batch_id: str
    inspection_type: str
    result: str
    inspector: str
    lab_name: str
    report_no: str
    detail: str
    inspect_date: str
    created_at: str


# ── 包装记录 ──────────────────────────────────────────────────────


class PackageCreate(BaseModel):
    batch_id: str
    package_date: str = Field(..., description="包装日期")
    weight_kg: float = Field(..., gt=0, description="重量（kg），必须大于 0")
    shelf_life_days: Optional[int] = None
    lot_number: str = Field(..., min_length=1, description="生产批号，必填")
    package_spec: str = Field("", description="包装规格")
    operator: str = ""


class Package(BaseModel):
    id: str
    batch_id: str
    package_date: str
    weight_kg: Optional[float] = None
    shelf_life_days: Optional[int] = None
    lot_number: str
    package_spec: str
    operator: str
    trace_code: Optional[str] = None
    created_at: str


# ── 溯源码 ──────────────────────────────────────────────────────


class TraceCode(BaseModel):
    id: str
    package_id: str
    batch_id: str
    code: str  # 唯一溯源码
    qr_url: str
    created_at: str
    is_active: bool = True
    data_hash: str = ""  # 数据哈希校验值
    data_scope: str = ""  # 包装时刻锁定的记录 ID 快照（JSON）


# ── 溯源报告（消费者查询结果） ──────────────────────────────────


class TraceReport(BaseModel):
    """消费者扫码看到的完整溯源报告"""

    batch_code: str
    plot_name: str
    plot_location: str
    seed_variety: str
    seed_supplier: str
    plant_date: str
    harvest_date: Optional[str] = None
    harvest_grade: Optional[str] = None
    harvest_yield_kg: Optional[float] = None
    activities_summary: Dict[str, int] = {}  # {"浇水": 3, "施肥": 2, ...}
    activities_detail: List[Dict[str, Any]] = []
    environment_summary: Dict[str, Any] = {}  # {"avg_temp": 25, "avg_humidity": 60}
    environment_detail: List[Dict[str, Any]] = []
    inspections: List[Dict[str, Any]] = []
    package_info: Optional[Dict[str, Any]] = None
    growth_photos: List[Dict[str, Any]] = []  # 生长照片
    harvest_photos: List[Dict[str, Any]] = []  # 采摘照片
    blockchain_verified: bool = False
    blockchain_hash: str = ""
    data_hash: str = ""  # 数据哈希校验值
    hash_verified: bool = True  # 哈希校验是否通过
    tamper_detected: bool = False  # 是否检测到篡改


# ── 溯源事件 ──────────────────────────────────────────────────────


class TraceEvent(BaseModel):
    event_id: str
    batch_id: str
    event_type: str
    event_name: str
    operator: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    note: Optional[str] = None
    created_at: str


# ── 批次照片 ──────────────────────────────────────────────────────


class BatchPhotoCreate(BaseModel):
    batch_id: str
    photo_type: str = Field(..., description="照片类型：growth-生长日常 / harvest-采摘时")
    photo_date: str = Field(..., description="照片日期")
    file_name: str = Field(..., description="原始文件名")
    note: str = ""


class BatchPhoto(BaseModel):
    id: str
    batch_id: str
    photo_type: str
    photo_date: str
    file_name: str
    file_path: str
    note: str = ""
    created_at: str


# ══════════════════════════════════════════════════════════════════════
#  数据库操作
# ══════════════════════════════════════════════════════════════════════


def _get_conn():
    if TRACE_DATABASE_BACKEND == "postgres":
        db_url = os.getenv("POSTGRES_URL", "").strip()
        if not db_url:
            raise RuntimeError("TRACE_DATABASE_BACKEND=postgres 时必须配置 POSTGRES_URL")
        conninfo = db_url.replace("+asyncpg", "").replace("+psycopg", "")
        return _PostgresConnection(conninfo)
    if TRACE_DATABASE_BACKEND != "sqlite":
        raise ValueError(f"不支持的 TRACE_DATABASE_BACKEND: {TRACE_DATABASE_BACKEND}")

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # 启用 WAL 模式提高并发性能
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def init_db():
    """初始化所有数据库表"""
    conn = _get_conn()
    c = conn.cursor()

    if TRACE_DATABASE_BACKEND == "postgres":
        if TRACE_DATABASE_SCHEMA_MODE == "validate":
            row = c.execute("SELECT to_regclass('traceability.plots') AS table_name").fetchone()
            conn.close()
            if not row or not row["table_name"]:
                raise RuntimeError("PostgreSQL 中尚未初始化 traceability schema，请先在班级节点执行迁移")
            return
        if TRACE_DATABASE_SCHEMA_MODE != "migrate":
            conn.close()
            raise ValueError(f"不支持的 TRACE_DATABASE_SCHEMA_MODE: {TRACE_DATABASE_SCHEMA_MODE}")
        c.execute("CREATE SCHEMA IF NOT EXISTS traceability")
        c.execute("SET search_path TO traceability, public")

    # 地块
    c.execute("""
        CREATE TABLE IF NOT EXISTS plots (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            area_mu REAL,
            soil_type TEXT,
            gps_lat REAL,
            gps_lng REAL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    # 种子
    c.execute("""
        CREATE TABLE IF NOT EXISTS seeds (
            id TEXT PRIMARY KEY,
            variety TEXT NOT NULL,
            supplier TEXT DEFAULT '',
            batch_no TEXT DEFAULT '',
            cert_info TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    # 种植批次
    c.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            batch_code TEXT NOT NULL UNIQUE,
            plot_id TEXT NOT NULL,
            seed_id TEXT NOT NULL,
            plant_date TEXT,
            expected_harvest_date TEXT,
            planting_method TEXT DEFAULT '',
            status TEXT DEFAULT 'growing',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (plot_id) REFERENCES plots(id),
            FOREIGN KEY (seed_id) REFERENCES seeds(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_batch_code ON batches(batch_code)")

    # 农事操作
    c.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            datetime TEXT NOT NULL,
            type TEXT NOT NULL,
            detail TEXT DEFAULT '',
            materials TEXT DEFAULT '',
            operator TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_activity_batch ON activities(batch_id)")

    # 环境数据
    c.execute("""
        CREATE TABLE IF NOT EXISTS environments (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            datetime TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            light_lux REAL,
            soil_moisture REAL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_env_batch ON environments(batch_id)")

    # 采摘记录
    c.execute("""
        CREATE TABLE IF NOT EXISTS harvests (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            harvest_date TEXT NOT NULL,
            yield_kg REAL,
            grade TEXT DEFAULT '',
            operator TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_harvest_batch ON harvests(batch_id)")

    # 质检记录
    c.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            inspection_type TEXT NOT NULL,
            result TEXT NOT NULL,
            inspector TEXT DEFAULT '',
            lab_name TEXT DEFAULT '',
            report_no TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            inspect_date TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_inspection_batch ON inspections(batch_id)")

    # 包装记录
    c.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            package_date TEXT NOT NULL,
            weight_kg REAL,
            shelf_life_days INTEGER,
            lot_number TEXT DEFAULT '',
            package_spec TEXT DEFAULT '',
            operator TEXT DEFAULT '',
            trace_code TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_package_batch ON packages(batch_id)")

    # 溯源码
    c.execute("""
        CREATE TABLE IF NOT EXISTS trace_codes (
            id TEXT PRIMARY KEY,
            package_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            qr_url TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            data_hash TEXT DEFAULT '',
            FOREIGN KEY (package_id) REFERENCES packages(id),
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_trace_code ON trace_codes(code)")

    # 溯源事件
    c.execute("""
        CREATE TABLE IF NOT EXISTS trace_events (
            event_id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_name TEXT NOT NULL,
            operator TEXT,
            result_json TEXT DEFAULT '{}',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_batch ON trace_events(batch_id)")

    # 演示区块链。PostgreSQL 模式下由所有学生节点共享。
    c.execute("""
        CREATE TABLE IF NOT EXISTS trace_blocks (
            block_index INTEGER PRIMARY KEY,
            timestamp DOUBLE PRECISION NOT NULL,
            data_json TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            hash TEXT NOT NULL,
            nonce INTEGER NOT NULL
        )
    """)

    # 批次照片（生长日常照片、采摘照片）
    c.execute("""
        CREATE TABLE IF NOT EXISTS batch_photos (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            photo_type TEXT NOT NULL,
            photo_date TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_photo_batch ON batch_photos(batch_id)")

    # 数据库迁移：补齐历史字段。
    if TRACE_DATABASE_BACKEND == "postgres":
        c.execute("ALTER TABLE trace_codes ADD COLUMN IF NOT EXISTS data_hash TEXT DEFAULT ''")
        c.execute("ALTER TABLE trace_codes ADD COLUMN IF NOT EXISTS data_scope TEXT DEFAULT ''")
    else:
        try:
            c.execute("ALTER TABLE trace_codes ADD COLUMN data_hash TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE trace_codes ADD COLUMN data_scope TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def _create_event(
    batch_id: str, event_type: str, event_name: str, operator: str = "", result: Dict = None, note: str = ""
):
    """创建溯源事件"""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO trace_events (event_id, batch_id, event_type, event_name, operator, result_json, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (
            _uid("EVT-"),
            batch_id,
            event_type,
            event_name,
            operator,
            json.dumps(result or {}, ensure_ascii=False),
            note,
            _now(),
        ),
    )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════
#  地块 CRUD
# ══════════════════════════════════════════════════════════════════════


def create_plot(data: PlotCreate) -> Plot:
    conn = _get_conn()
    pid = _uid("PLT-")
    now = _now()
    conn.execute(
        "INSERT INTO plots (id, name, location, area_mu, soil_type, gps_lat, gps_lng, note, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (pid, data.name, data.location, data.area_mu, data.soil_type, data.gps_lat, data.gps_lng, data.note, now),
    )
    conn.commit()
    conn.close()
    return get_plot(pid)


def get_plot(pid: str) -> Optional[Plot]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM plots WHERE id = ?", (pid,)).fetchone()
    conn.close()
    if not row:
        return None
    return Plot(**dict(row))


def list_plots() -> List[Plot]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM plots ORDER BY created_at DESC").fetchall()
    conn.close()
    return [Plot(**dict(r)) for r in rows]


def update_plot(pid: str, patch: PlotUpdate) -> Optional[Plot]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM plots WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        return None
    updates = {k: v for k, v in patch.model_dump().items() if v is not None}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE plots SET {set_clause} WHERE id = ?", (*updates.values(), pid))
        conn.commit()
    conn.close()
    return get_plot(pid)


def delete_plot(pid: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM plots WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════
#  种子 CRUD
# ══════════════════════════════════════════════════════════════════════


def create_seed(data: SeedCreate) -> Seed:
    conn = _get_conn()
    sid = _uid("SEED-")
    conn.execute(
        "INSERT INTO seeds (id, variety, supplier, batch_no, cert_info, note, created_at) VALUES (?,?,?,?,?,?,?)",
        (sid, data.variety, data.supplier, data.batch_no, data.cert_info, data.note, _now()),
    )
    conn.commit()
    conn.close()
    return get_seed(sid)


def get_seed(sid: str) -> Optional[Seed]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM seeds WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not row:
        return None
    return Seed(**dict(row))


def list_seeds() -> List[Seed]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM seeds ORDER BY created_at DESC").fetchall()
    conn.close()
    return [Seed(**dict(r)) for r in rows]


def update_seed(sid: str, patch: SeedUpdate) -> Optional[Seed]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM seeds WHERE id = ?", (sid,)).fetchone()
    if not row:
        conn.close()
        return None
    updates = {k: v for k, v in patch.model_dump().items() if v is not None}
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE seeds SET {set_clause} WHERE id = ?", (*updates.values(), sid))
        conn.commit()
    conn.close()
    return get_seed(sid)


def delete_seed(sid: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM seeds WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════
#  种植批次 CRUD
# ══════════════════════════════════════════════════════════════════════


def create_batch(data: BatchCreate) -> Batch:
    # 检查批次编号是否重复
    existing = get_batch_by_code(data.batch_code)
    if existing:
        raise ValueError(f"批次编号 {data.batch_code} 已存在")

    conn = _get_conn()
    bid = _uid("BATCH-")
    now = _now()
    conn.execute(
        "INSERT INTO batches (id, batch_code, plot_id, seed_id, plant_date, expected_harvest_date, planting_method, note, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            bid,
            data.batch_code,
            data.plot_id,
            data.seed_id,
            data.plant_date,
            data.expected_harvest_date,
            data.planting_method,
            data.note,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    _create_event(bid, "batch_created", "创建种植批次", note=f"批次={data.batch_code}")
    return get_batch(bid)


def get_batch(bid: str) -> Optional[Batch]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM batches WHERE id = ?", (bid,)).fetchone()
    if not row:
        conn.close()
        return None

    # 查询关联数据
    plot = None
    if row["plot_id"]:
        prow = conn.execute("SELECT * FROM plots WHERE id = ?", (row["plot_id"],)).fetchone()
        if prow:
            plot = Plot(**dict(prow))

    seed = None
    if row["seed_id"]:
        srow = conn.execute("SELECT * FROM seeds WHERE id = ?", (row["seed_id"],)).fetchone()
        if srow:
            seed = Seed(**dict(srow))

    activities = [
        dict(r)
        for r in conn.execute("SELECT * FROM activities WHERE batch_id = ? ORDER BY datetime", (bid,)).fetchall()
    ]
    environments = [
        dict(r)
        for r in conn.execute("SELECT * FROM environments WHERE batch_id = ? ORDER BY datetime", (bid,)).fetchall()
    ]
    harvests = [
        dict(r)
        for r in conn.execute("SELECT * FROM harvests WHERE batch_id = ? ORDER BY harvest_date", (bid,)).fetchall()
    ]
    inspections = [
        dict(r)
        for r in conn.execute("SELECT * FROM inspections WHERE batch_id = ? ORDER BY inspect_date", (bid,)).fetchall()
    ]
    packages = [
        dict(r)
        for r in conn.execute("SELECT * FROM packages WHERE batch_id = ? ORDER BY package_date", (bid,)).fetchall()
    ]

    conn.close()

    return Batch(
        id=row["id"],
        batch_code=row["batch_code"],
        plot_id=row["plot_id"],
        seed_id=row["seed_id"],
        plant_date=row["plant_date"],
        expected_harvest_date=row["expected_harvest_date"],
        planting_method=row["planting_method"] or "",
        status=row["status"] or "growing",
        note=row["note"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        plot=plot,
        seed=seed,
        activities=activities,
        environments=environments,
        harvests=harvests,
        inspections=inspections,
        packages=packages,
    )


def get_batch_by_code(batch_code: str) -> Optional[Batch]:
    conn = _get_conn()
    row = conn.execute("SELECT id FROM batches WHERE batch_code = ?", (batch_code,)).fetchone()
    conn.close()
    if not row:
        return None
    return get_batch(row["id"])


def list_batches(limit: int = 50) -> List[Batch]:
    conn = _get_conn()
    rows = conn.execute("SELECT id FROM batches ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [get_batch(r["id"]) for r in rows]


def update_batch(bid: str, patch: BatchUpdate) -> Optional[Batch]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM batches WHERE id = ?", (bid,)).fetchone()
    if not row:
        conn.close()
        return None
    updates = {k: v for k, v in patch.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE batches SET {set_clause} WHERE id = ?", (*updates.values(), bid))
        conn.commit()
    conn.close()
    _create_event(bid, "batch_updated", "更新种植批次", note=f"更新字段: {list(updates.keys())}")
    return get_batch(bid)


def delete_batch(bid: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM activities WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM environments WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM harvests WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM inspections WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM trace_codes WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM packages WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM trace_events WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM batch_photos WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM batches WHERE id = ?", (bid,))
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════
#  农事操作
# ══════════════════════════════════════════════════════════════════════


def add_activity(data: ActivityCreate) -> Activity:
    conn = _get_conn()
    aid = _uid("ACT-")
    conn.execute(
        "INSERT INTO activities (id, batch_id, datetime, type, detail, materials, operator, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (aid, data.batch_id, data.datetime, data.type, data.detail, data.materials, data.operator, _now()),
    )
    conn.commit()
    conn.close()
    _create_event(
        data.batch_id,
        "activity_recorded",
        f"记录{data.type}",
        operator=data.operator,
        note=f"{data.detail} {data.materials}",
    )
    return Activity(
        id=aid,
        batch_id=data.batch_id,
        datetime=data.datetime,
        type=data.type,
        detail=data.detail,
        materials=data.materials,
        operator=data.operator,
        created_at=_now(),
    )


def list_activities(batch_id: str) -> List[Activity]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM activities WHERE batch_id = ? ORDER BY datetime", (batch_id,)).fetchall()
    conn.close()
    return [Activity(**dict(r)) for r in rows]


def delete_activity(aid: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM activities WHERE id = ?", (aid,))
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════
#  环境数据
# ══════════════════════════════════════════════════════════════════════


def add_environment(data: EnvironmentCreate) -> Environment:
    conn = _get_conn()
    eid = _uid("ENV-")
    conn.execute(
        "INSERT INTO environments (id, batch_id, datetime, temperature, humidity, light_lux, soil_moisture, note, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            eid,
            data.batch_id,
            data.datetime,
            data.temperature,
            data.humidity,
            data.light_lux,
            data.soil_moisture,
            data.note,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    _create_event(
        data.batch_id, "environment_recorded", "记录环境数据", note=f"温度={data.temperature}℃ 湿度={data.humidity}%"
    )
    return Environment(
        id=eid,
        batch_id=data.batch_id,
        datetime=data.datetime,
        temperature=data.temperature,
        humidity=data.humidity,
        light_lux=data.light_lux,
        soil_moisture=data.soil_moisture,
        note=data.note,
        created_at=_now(),
    )


def list_environments(batch_id: str) -> List[Environment]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM environments WHERE batch_id = ? ORDER BY datetime", (batch_id,)).fetchall()
    conn.close()
    return [Environment(**dict(r)) for r in rows]


def delete_environment(eid: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM environments WHERE id = ?", (eid,))
    conn.commit()
    conn.close()
    return True


# ══════════════════════════════════════════════════════════════════════
#  采摘记录
# ══════════════════════════════════════════════════════════════════════


def add_harvest(data: HarvestCreate) -> Harvest:
    conn = _get_conn()
    hid = _uid("HV-")
    conn.execute(
        "INSERT INTO harvests (id, batch_id, harvest_date, yield_kg, grade, operator, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (hid, data.batch_id, data.harvest_date, data.yield_kg, data.grade, data.operator, data.note, _now()),
    )
    # 更新批次状态
    conn.execute("UPDATE batches SET status = 'harvested', updated_at = ? WHERE id = ?", (_now(), data.batch_id))
    conn.commit()
    conn.close()
    _create_event(
        data.batch_id,
        "harvest_recorded",
        "记录采摘",
        operator=data.operator,
        note=f"产量={data.yield_kg}kg 等级={data.grade}",
    )
    return Harvest(
        id=hid,
        batch_id=data.batch_id,
        harvest_date=data.harvest_date,
        yield_kg=data.yield_kg,
        grade=data.grade,
        operator=data.operator,
        note=data.note,
        created_at=_now(),
    )


def list_harvests(batch_id: str) -> List[Harvest]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM harvests WHERE batch_id = ? ORDER BY harvest_date", (batch_id,)).fetchall()
    conn.close()
    return [Harvest(**dict(r)) for r in rows]


# ══════════════════════════════════════════════════════════════════════
#  质检记录
# ══════════════════════════════════════════════════════════════════════


def add_inspection(data: InspectionCreate) -> Inspection:
    conn = _get_conn()
    iid = _uid("QC-")
    conn.execute(
        "INSERT INTO inspections (id, batch_id, inspection_type, result, inspector, lab_name, report_no, detail, inspect_date, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            iid,
            data.batch_id,
            data.inspection_type,
            data.result,
            data.inspector,
            data.lab_name,
            data.report_no,
            data.detail,
            data.inspect_date,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    _create_event(
        data.batch_id,
        "inspection_recorded",
        f"质检-{data.inspection_type}",
        operator=data.inspector,
        note=f"结果={data.result}",
    )
    return Inspection(
        id=iid,
        batch_id=data.batch_id,
        inspection_type=data.inspection_type,
        result=data.result,
        inspector=data.inspector,
        lab_name=data.lab_name,
        report_no=data.report_no,
        detail=data.detail,
        inspect_date=data.inspect_date,
        created_at=_now(),
    )


def list_inspections(batch_id: str) -> List[Inspection]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM inspections WHERE batch_id = ? ORDER BY inspect_date", (batch_id,)).fetchall()
    conn.close()
    return [Inspection(**dict(r)) for r in rows]


# ══════════════════════════════════════════════════════════════════════
#  包装记录
# ══════════════════════════════════════════════════════════════════════


def add_package(data: PackageCreate) -> Package:
    conn = _get_conn()
    pid = _uid("PKG-")
    conn.execute(
        "INSERT INTO packages (id, batch_id, package_date, weight_kg, shelf_life_days, lot_number, package_spec, operator, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            pid,
            data.batch_id,
            data.package_date,
            data.weight_kg,
            data.shelf_life_days,
            data.lot_number,
            data.package_spec,
            data.operator,
            _now(),
        ),
    )
    # 更新批次状态
    conn.execute("UPDATE batches SET status = 'packaged', updated_at = ? WHERE id = ?", (_now(), data.batch_id))
    conn.commit()
    conn.close()
    _create_event(
        data.batch_id,
        "package_recorded",
        "记录包装",
        operator=data.operator,
        note=f"重量={data.weight_kg}kg 规格={data.package_spec}",
    )

    # 自动生成溯源码
    generate_trace_code(pid, data.batch_id)

    return get_package(pid)


def get_package(pid: str) -> Optional[Package]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM packages WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        return None
    tc_row = conn.execute("SELECT code FROM trace_codes WHERE package_id = ?", (pid,)).fetchone()
    conn.close()
    d = dict(row)
    d["trace_code"] = tc_row["code"] if tc_row else None
    return Package(**d)


def list_packages(batch_id: str) -> List[Package]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM packages WHERE batch_id = ? ORDER BY package_date", (batch_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        tc_row = conn.execute("SELECT code FROM trace_codes WHERE package_id = ?", (r["id"],)).fetchone()
        d["trace_code"] = tc_row["code"] if tc_row else None
        result.append(Package(**d))
    conn.close()
    return result


# ══════════════════════════════════════════════════════════════════════
#  溯源码
# ══════════════════════════════════════════════════════════════════════


def _rows_for_scope(batch_id: str, data_scope: Optional[List[str]]) -> Dict[str, List[Dict[str, Any]]]:
    """读取指定批次各类型记录，data_scope 非空时仅保留锁定的记录 ID。"""
    conn = _get_conn()
    result: Dict[str, List[Dict[str, Any]]] = {}
    for table in ("activities", "environments", "harvests", "inspections"):
        rows = conn.execute(f"SELECT * FROM {table} WHERE batch_id = ?", (batch_id,)).fetchall()
        items = [dict(r) for r in rows]
        if data_scope is not None:
            items = [d for d in items if d["id"] in data_scope]
        result[table] = items
    conn.close()
    return result


def _calculate_data_hash(batch_id: str, package_id: str, code: str, data_scope: Optional[List[str]] = None) -> str:
    """计算溯源数据哈希值，用于校验数据完整性。

    校验语义基于「包装时刻快照」：
    - 包装之前已存在的采摘/质检/环境/农事记录属于该包装的来源信息，必须被锁定校验；
    - 包装之后新追加的记录与该包装无关，不应参与校验。
    因此只对 data_scope 锁定的记录 ID 重新读取并参与哈希；
    data_scope 为 None 时（生成溯源码时）锁定当前全部记录。
    """
    conn = _get_conn()
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    package = conn.execute("SELECT * FROM packages WHERE id = ?", (package_id,)).fetchone()
    conn.close()

    # 构建数据摘要（排除 trace_code 字段，因为它是在哈希计算后才更新的）
    pkg_dict = dict(package) if package else {}
    pkg_dict.pop("trace_code", None)  # 移除 trace_code 字段

    scoped = _rows_for_scope(batch_id, data_scope)
    data_parts = [
        f"code:{code}",
        f"batch_code:{batch['batch_code'] if batch else ''}",
        f"package:{pkg_dict}",
        f"activities:{scoped['activities']}",
        f"environments:{scoped['environments']}",
        f"harvests:{scoped['harvests']}",
        f"inspections:{scoped['inspections']}",
    ]
    data_str = "|".join(str(part) for part in data_parts)
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def _calculate_legacy_data_hash(batch_id: str, package_id: str, code: str) -> str:
    """旧版溯源数据哈希（兼容历史溯源码，保持原校验语义不变）。"""
    conn = _get_conn()
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    package = conn.execute("SELECT * FROM packages WHERE id = ?", (package_id,)).fetchone()
    activities = conn.execute("SELECT * FROM activities WHERE batch_id = ?", (batch_id,)).fetchall()
    environments = conn.execute("SELECT * FROM environments WHERE batch_id = ?", (batch_id,)).fetchall()
    harvests = conn.execute("SELECT * FROM harvests WHERE batch_id = ?", (batch_id,)).fetchall()
    inspections = conn.execute("SELECT * FROM inspections WHERE batch_id = ?", (batch_id,)).fetchall()
    conn.close()

    # 构建数据摘要（排除 trace_code 字段，因为它是在哈希计算后才更新的）
    pkg_dict = dict(package) if package else {}
    pkg_dict.pop("trace_code", None)  # 移除 trace_code 字段

    data_parts = [
        f"code:{code}",
        f"batch:{dict(batch) if batch else ''}",
        f"package:{pkg_dict}",
        f"activities:{[dict(a) for a in activities]}",
        f"environments:{[dict(e) for e in environments]}",
        f"harvests:{[dict(h) for h in harvests]}",
        f"inspections:{[dict(i) for i in inspections]}",
    ]
    data_str = "|".join(str(part) for part in data_parts)
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def generate_trace_code(package_id: str, batch_id: str) -> TraceCode:
    """为包装生成唯一溯源码"""
    conn = _get_conn()
    code = f"TM{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    tcid = _uid("TC-")
    qr_url = f"/api/trace/{code}"

    # 锁定包装时刻已存在的记录 ID 快照（采摘/质检/环境/农事）
    scope_ids = {
        "activities": [
            r["id"] for r in conn.execute("SELECT id FROM activities WHERE batch_id = ?", (batch_id,)).fetchall()
        ],
        "environments": [
            r["id"] for r in conn.execute("SELECT id FROM environments WHERE batch_id = ?", (batch_id,)).fetchall()
        ],
        "harvests": [
            r["id"] for r in conn.execute("SELECT id FROM harvests WHERE batch_id = ?", (batch_id,)).fetchall()
        ],
        "inspections": [
            r["id"] for r in conn.execute("SELECT id FROM inspections WHERE batch_id = ?", (batch_id,)).fetchall()
        ],
    }
    data_scope = json.dumps(scope_ids, ensure_ascii=False)

    # 计算数据哈希（锁定当前全部记录）
    data_hash = _calculate_data_hash(batch_id, package_id, code)

    conn.execute(
        "INSERT INTO trace_codes (id, package_id, batch_id, code, qr_url, created_at, data_hash, data_scope) VALUES (?,?,?,?,?,?,?,?)",
        (tcid, package_id, batch_id, code, qr_url, _now(), data_hash, data_scope),
    )
    # 回写到包装记录
    conn.execute("UPDATE packages SET trace_code = ? WHERE id = ?", (code, package_id))
    conn.commit()
    conn.close()
    _create_event(batch_id, "trace_code_generated", "生成溯源码", note=f"溯源码={code}")
    return TraceCode(
        id=tcid,
        package_id=package_id,
        batch_id=batch_id,
        code=code,
        qr_url=qr_url,
        created_at=_now(),
        data_hash=data_hash,
        data_scope=data_scope,
    )


def get_trace_code(code: str) -> Optional[TraceCode]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM trace_codes WHERE code = ? AND is_active = 1", (code,)).fetchone()
    conn.close()
    if not row:
        return None
    return TraceCode(**dict(row))


# ══════════════════════════════════════════════════════════════════════
#  溯源报告（消费者查询）
# ══════════════════════════════════════════════════════════════════════


def get_trace_report(code: str) -> Optional[TraceReport]:
    """根据溯源码生成完整溯源报告"""
    tc = get_trace_code(code)
    if not tc:
        return None

    batch = get_batch(tc.batch_id)
    if not batch:
        return None

    # 验证数据哈希
    # - 新溯源码：只对包装时刻锁定的记录重新哈希，包装后追加的记录不参与校验
    # - 旧溯源码（data_scope 为空）：沿用旧版哈希公式，保持历史校验语义
    if tc.data_scope:
        try:
            scope_map = json.loads(tc.data_scope)
            scope_ids = (
                scope_map.get("activities", [])
                + scope_map.get("environments", [])
                + scope_map.get("harvests", [])
                + scope_map.get("inspections", [])
            )
        except (ValueError, AttributeError):
            scope_ids = None  # 数据异常时退回全量校验
        current_hash = _calculate_data_hash(tc.batch_id, tc.package_id, tc.code, data_scope=scope_ids)
    else:
        current_hash = _calculate_legacy_data_hash(tc.batch_id, tc.package_id, tc.code)
    hash_verified = current_hash == tc.data_hash
    tamper_detected = not hash_verified

    # 统计农事操作
    activities_summary = {}
    for a in batch.activities:
        t = a.get("type", "其他")
        activities_summary[t] = activities_summary.get(t, 0) + 1

    # 计算环境数据平均值
    env_data = batch.environments
    env_summary = {}
    if env_data:
        temps = [e["temperature"] for e in env_data if e.get("temperature") is not None]
        humids = [e["humidity"] for e in env_data if e.get("humidity") is not None]
        if temps:
            env_summary["avg_temp"] = round(sum(temps) / len(temps), 1)
        if humids:
            env_summary["avg_humidity"] = round(sum(humids) / len(humids), 1)
        env_summary["record_count"] = len(env_data)

    # 最近的采摘
    harvest_date = None
    harvest_grade = None
    harvest_yield = None
    if batch.harvests:
        h = batch.harvests[-1]
        harvest_date = h.get("harvest_date")
        harvest_grade = h.get("grade")
        harvest_yield = h.get("yield_kg")

    # 包装信息
    pkg_info = None
    if batch.packages:
        p = batch.packages[-1]
        pkg_info = {
            "package_date": p.get("package_date"),
            "weight_kg": p.get("weight_kg"),
            "shelf_life_days": p.get("shelf_life_days"),
            "lot_number": p.get("lot_number"),
            "package_spec": p.get("package_spec"),
        }

    # 获取照片
    growth_photos = list_batch_photos(tc.batch_id, "growth")
    harvest_photos = list_batch_photos(tc.batch_id, "harvest")

    return TraceReport(
        batch_code=batch.batch_code,
        plot_name=batch.plot.name if batch.plot else "",
        plot_location=batch.plot.location if batch.plot else "",
        seed_variety=batch.seed.variety if batch.seed else "",
        seed_supplier=batch.seed.supplier if batch.seed else "",
        plant_date=batch.plant_date or "",
        harvest_date=harvest_date,
        harvest_grade=harvest_grade,
        harvest_yield_kg=harvest_yield,
        activities_summary=activities_summary,
        activities_detail=[
            {
                "type": a.get("type"),
                "datetime": a.get("datetime"),
                "detail": a.get("detail"),
                "materials": a.get("materials"),
            }
            for a in batch.activities
        ],
        environment_summary=env_summary,
        environment_detail=[
            {"datetime": e.get("datetime"), "temperature": e.get("temperature"), "humidity": e.get("humidity")}
            for e in batch.environments
        ],
        inspections=[
            {
                "type": i.get("inspection_type"),
                "result": i.get("result"),
                "lab": i.get("lab_name"),
                "date": i.get("inspect_date"),
            }
            for i in batch.inspections
        ],
        package_info=pkg_info,
        growth_photos=[p.model_dump() for p in growth_photos],
        harvest_photos=[p.model_dump() for p in harvest_photos],
        data_hash=tc.data_hash,
        hash_verified=hash_verified,
        tamper_detected=tamper_detected,
    )


# ══════════════════════════════════════════════════════════════════════
#  溯源事件
# ══════════════════════════════════════════════════════════════════════


def list_events(batch_id: str) -> List[TraceEvent]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM trace_events WHERE batch_id = ? ORDER BY created_at", (batch_id,)).fetchall()
    conn.close()
    return [
        TraceEvent(
            event_id=r["event_id"],
            batch_id=r["batch_id"],
            event_type=r["event_type"],
            event_name=r["event_name"],
            operator=r["operator"],
            result=json.loads(r["result_json"] or "{}"),
            note=r["note"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


# ══════════════════════════════════════════════════════════════════════
#  批次照片
# ══════════════════════════════════════════════════════════════════════


def add_batch_photo(data: BatchPhotoCreate, file_path: str) -> BatchPhoto:
    conn = _get_conn()
    pid = _uid("PHOTO-")
    conn.execute(
        "INSERT INTO batch_photos (id, batch_id, photo_type, photo_date, file_name, file_path, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (pid, data.batch_id, data.photo_type, data.photo_date, data.file_name, file_path, data.note, _now()),
    )
    conn.commit()
    conn.close()
    photo_type_name = "生长日常" if data.photo_type == "growth" else "采摘时"
    _create_event(data.batch_id, "photo_uploaded", f"上传{photo_type_name}照片", note=f"文件={data.file_name}")
    return BatchPhoto(
        id=pid,
        batch_id=data.batch_id,
        photo_type=data.photo_type,
        photo_date=data.photo_date,
        file_name=data.file_name,
        file_path=file_path,
        note=data.note,
        created_at=_now(),
    )


def list_batch_photos(batch_id: str, photo_type: Optional[str] = None) -> List[BatchPhoto]:
    conn = _get_conn()
    if photo_type:
        rows = conn.execute(
            "SELECT * FROM batch_photos WHERE batch_id = ? AND photo_type = ? ORDER BY photo_date DESC",
            (batch_id, photo_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM batch_photos WHERE batch_id = ? ORDER BY photo_date DESC", (batch_id,)
        ).fetchall()
    conn.close()
    return [BatchPhoto(**dict(r)) for r in rows]


def get_batch_photo(photo_id: str) -> Optional[BatchPhoto]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM batch_photos WHERE id = ?", (photo_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return BatchPhoto(**dict(row))


def delete_batch_photo(photo_id: str) -> bool:
    conn = _get_conn()
    photo = conn.execute("SELECT file_path FROM batch_photos WHERE id = ?", (photo_id,)).fetchone()
    if photo:
        conn.execute("DELETE FROM batch_photos WHERE id = ?", (photo_id,))
        conn.commit()
    conn.close()
    return photo is not None


# ══════════════════════════════════════════════════════════════════════
#  统计
# ══════════════════════════════════════════════════════════════════════


def get_stats() -> Dict[str, Any]:
    conn = _get_conn()
    stats = {
        "total_plots": conn.execute("SELECT COUNT(*) AS value FROM plots").fetchone()["value"],
        "total_seeds": conn.execute("SELECT COUNT(*) AS value FROM seeds").fetchone()["value"],
        "total_batches": conn.execute("SELECT COUNT(*) AS value FROM batches").fetchone()["value"],
        "total_activities": conn.execute("SELECT COUNT(*) AS value FROM activities").fetchone()["value"],
        "total_environments": conn.execute("SELECT COUNT(*) AS value FROM environments").fetchone()["value"],
        "total_harvests": conn.execute("SELECT COUNT(*) AS value FROM harvests").fetchone()["value"],
        "total_inspections": conn.execute("SELECT COUNT(*) AS value FROM inspections").fetchone()["value"],
        "total_packages": conn.execute("SELECT COUNT(*) AS value FROM packages").fetchone()["value"],
        "total_trace_codes": conn.execute("SELECT COUNT(*) AS value FROM trace_codes").fetchone()["value"],
    }
    conn.close()
    return stats
