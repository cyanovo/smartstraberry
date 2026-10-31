"""番茄溯源数据库层 — 单元测试

覆盖：
1. 包装记录必填校验（日期 + 重量>0 + 批次号）
2. 溯源码数据完整性校验：包装后再追加采摘/质检/环境不应误报篡改
"""

from __future__ import annotations

import os
import tempfile

import pytest

from yuxi.traceability import db

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolated_trace_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """每个测试使用独立的临时 SQLite 库，避免污染真实数据。"""
    tmp = os.path.join(tempfile.mkdtemp(), "trace_test.db")
    monkeypatch.setattr(db, "DB_PATH", tmp)
    db.init_db()


@pytest.fixture
def batch() -> db.Batch:
    plot = db.create_plot(db.PlotCreate(name="测试地块", location="A区"))
    seed = db.create_seed(db.SeedCreate(variety="粉果番茄", supplier="中蔬"))
    return db.create_batch(
        db.BatchCreate(
            batch_code="TEST-BATCH-001",
            plot_id=plot.id,
            seed_id=seed.id,
            plant_date="2026-08-01",
        )
    )


# ══════════════════════════════════════════════════════════════════════
#  包装记录必填校验
# ══════════════════════════════════════════════════════════════════════

def test_add_package_rejects_empty_payload(batch) -> None:
    """包装日期、重量、批次号均必填；空包装必须被拒绝。"""
    with pytest.raises(ValueError):
        db.add_package(db.PackageCreate(batch_id=batch.id, package_date="2026-08-05"))


def test_add_package_rejects_zero_weight(batch) -> None:
    """重量必须大于 0。"""
    with pytest.raises(ValueError):
        db.add_package(
            db.PackageCreate(
                batch_id=batch.id,
                package_date="2026-08-05",
                weight_kg=0,
                lot_number="LOT-001",
            )
        )


def test_add_package_rejects_missing_lot_number(batch) -> None:
    """批次号必须填写。"""
    with pytest.raises(ValueError):
        db.add_package(
            db.PackageCreate(
                batch_id=batch.id,
                package_date="2026-08-05",
                weight_kg=5.0,
                lot_number="",
            )
        )


def test_add_package_succeeds_with_required_fields(batch) -> None:
    """填写日期 + 重量 + 批次号后可正常创建，并生成溯源码。"""
    pkg = db.add_package(
        db.PackageCreate(
            batch_id=batch.id,
            package_date="2026-08-05",
            weight_kg=5.0,
            lot_number="LOT-001",
        )
    )
    assert pkg.trace_code is not None
    assert pkg.trace_code.startswith("TM")


# ══════════════════════════════════════════════════════════════════════
#  溯源码数据完整性校验
# ══════════════════════════════════════════════════════════════════════

def _create_package(batch) -> db.Package:
    return db.add_package(
        db.PackageCreate(
            batch_id=batch.id,
            package_date="2026-08-05",
            weight_kg=5.0,
            lot_number="LOT-001",
        )
    )


def test_trace_report_verifies_immediately_after_package(batch) -> None:
    """创建包装后立即查询，校验应通过。"""
    pkg = _create_package(batch)
    report = db.get_trace_report(pkg.trace_code)
    assert report is not None
    assert report.hash_verified is True
    assert report.tamper_detected is False


def test_trace_report_stays_valid_after_adding_harvest(batch) -> None:
    """包装之后再追加采摘/质检/环境记录，不应误报篡改。"""
    pkg = _create_package(batch)

    db.add_harvest(
        db.HarvestCreate(batch_id=batch.id, harvest_date="2026-08-06", yield_kg=100.0, grade="特级")
    )
    db.add_inspection(
        db.InspectionCreate(batch_id=batch.id, inspection_type="农残", result="合格")
    )
    db.add_environment(
        db.EnvironmentCreate(batch_id=batch.id, datetime="2026-08-06", temperature=25.0, humidity=60.0)
    )

    report = db.get_trace_report(pkg.trace_code)
    assert report is not None
    assert report.hash_verified is True, "包装后追加合法数据不应导致校验失败"
    assert report.tamper_detected is False


def test_trace_report_stays_valid_after_batch_status_change(batch) -> None:
    """包装后更新批次状态（如标记已销售），不应误报篡改。"""
    pkg = _create_package(batch)

    db.update_batch(batch.id, db.BatchUpdate(status="sold"))

    report = db.get_trace_report(pkg.trace_code)
    assert report is not None
    assert report.hash_verified is True, "包装后更新批次状态不应导致校验失败"
    assert report.tamper_detected is False


def test_trace_report_detects_tampering_of_pre_package_harvest(batch) -> None:
    """包装之前已存在的采摘记录被修改，必须检测到篡改。"""
    harvest = db.add_harvest(
        db.HarvestCreate(batch_id=batch.id, harvest_date="2026-08-03", yield_kg=100.0, grade="特级")
    )
    pkg = _create_package(batch)

    # 包装后直接篡改包装前已锁定的采摘记录
    conn = db._get_conn()
    conn.execute(
        "UPDATE harvests SET yield_kg = 999.0 WHERE id = ?", (harvest.id,)
    )
    conn.commit()
    conn.close()

    report = db.get_trace_report(pkg.trace_code)
    assert report is not None
    assert report.tamper_detected is True, "包装前记录被篡改必须检测到异常"
    assert report.hash_verified is False


def test_trace_report_detects_tampering_of_pre_package_inspection(batch) -> None:
    """包装之前已存在的质检记录被修改，必须检测到篡改。"""
    inspection = db.add_inspection(
        db.InspectionCreate(batch_id=batch.id, inspection_type="农残", result="合格")
    )
    pkg = _create_package(batch)

    conn = db._get_conn()
    conn.execute(
        "UPDATE inspections SET result = '不合格' WHERE id = ?", (inspection.id,)
    )
    conn.commit()
    conn.close()

    report = db.get_trace_report(pkg.trace_code)
    assert report is not None
    assert report.tamper_detected is True, "包装前质检被篡改必须检测到异常"
    assert report.hash_verified is False
