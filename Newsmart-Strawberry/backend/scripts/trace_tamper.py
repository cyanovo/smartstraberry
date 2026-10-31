#!/usr/bin/env python
"""
番茄溯源 — 篡改模拟工具（开发用）

在真实溯源 SQLite 库上模拟「数据篡改」，用于验证溯源码的完整性检测
（hash_verified / tamper_detected）。本程序是独立命令行工具，不属于 Web
应用，不占用任何 HTTP 接口，仅供开发/测试人员在容器内使用。

每次修改都会先把原值记录到临时备份表 `tamper_backup`，可用 `undo` 一键还原。

用法（容器内，/app 目录）：
    python scripts/trace_tamper.py                       # 进入交互式命令行
    python scripts/trace_tamper.py --db 其他.db 命令 ...  # 指定数据库并直跑命令
    python scripts/trace_tamper.py status TM2026...      # 单条命令

命令：
    list-batches                       列出所有批次
    list-harvests <batch_id>           列出某批次的采摘记录
    list-inspections <batch_id>        列出某批次的质检记录
    list-environments <batch_id>       列出某批次的环境记录
    list-activities <batch_id>         列出某批次的农事记录
    modify-harvest <id> <字段>=<值>     篡改采摘记录字段（如 yield_kg=999）
    modify-inspection <id> <字段>=<值>  篡改质检记录字段（如 result=不合格）
    modify-environment <id> <字段>=<值> 篡改环境记录字段（如 temperature=99）
    modify-activity <id> <字段>=<值>    篡改农事记录字段
    delete-harvest <id>                删除采摘记录
    delete-inspection <id>             删除质检记录
    status <trace_code>                查询溯源码的完整性校验结果
    undo <id>                          还原对某条记录的最近一次修改
    help                               显示帮助
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# 与 db.py 使用相同的数据库路径解析（Docker 卷 / 本地回退）
_SAVES_DIR = Path("/app/saves") if Path("/app/saves").exists() else Path(__file__).resolve().parents[1] / "docker" / "volumes" / "greenhouse"
DEFAULT_DB = _SAVES_DIR / ".tomato_trace.db"

# 可篡改的记录类型 → 表名
TABLES = {
    "harvest": "harvests",
    "inspection": "inspections",
    "environment": "environments",
    "activity": "activities",
}
TABLE_LABELS = {
    "harvests": "采摘",
    "inspections": "质检",
    "environments": "环境",
    "activities": "农事",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # 备份表：记录每次篡改前的原值，供 undo 还原
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tamper_backup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            old_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    return conn


def _dump(rows) -> None:
    for r in rows:
        d = dict(r)
        # 长字段截断，避免刷屏
        for k in list(d):
            if isinstance(d[k], str) and len(d[k]) > 40:
                d[k] = d[k][:40] + "..."
        print(json.dumps(d, ensure_ascii=False))


def _get_by_id(conn, table: str, rid: str) -> sqlite3.Row | None:
    return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (rid,)).fetchone()


def _backup(conn, table: str, rid: str, row: sqlite3.Row) -> None:
    conn.execute(
        "INSERT INTO tamper_backup (record_type, record_id, old_json) VALUES (?,?,?)",
        (table, rid, json.dumps(dict(row), ensure_ascii=False)),
    )


# ══════════════════════════════════════════════════════════════════════
#  各命令实现
# ══════════════════════════════════════════════════════════════════════

def _list_batches(conn) -> None:
    rows = conn.execute("SELECT id, batch_code, status, created_at FROM batches ORDER BY created_at").fetchall()
    if not rows:
        print("(无批次)")
        return
    _dump(rows)


def _list_records(conn, table: str, batch_id: str) -> None:
    rows = conn.execute(f"SELECT * FROM {table} WHERE batch_id = ? ORDER BY created_at", (batch_id,)).fetchall()
    label = TABLE_LABELS.get(table, table)
    if not rows:
        print(f"批次 {batch_id} 暂无{label}记录")
        return
    print(f"批次 {batch_id} 的{label}记录:")
    _dump(rows)


def _modify(conn, record_type: str, rid: str, field: str, value: str) -> None:
    table = TABLES.get(record_type)
    if table is None:
        print(f"未知记录类型: {record_type}（可用: {', '.join(TABLES)}）")
        return
    row = _get_by_id(conn, table, rid)
    if not row:
        print(f"{record_type} 记录不存在: {rid}")
        return
    if field not in row.keys():
        print(f"字段不存在: {field}（该表字段: {', '.join(row.keys())}）")
        return

    # 尝试转类型（数字列自动转换，文本列保持原样）
    current = row[field]
    if current is not None and isinstance(current, (int, float)):
        try:
            new_val = float(value) if isinstance(current, float) else int(value)
        except ValueError:
            print(f"字段 {field} 是数值类型，值 '{value}' 无法转换")
            return
    else:
        new_val = value

    _backup(conn, table, rid, row)
    conn.execute(f"UPDATE {table} SET {field} = ? WHERE id = ?", (new_val, rid))
    conn.commit()
    print(f"已篡改 {TABLE_LABELS.get(table)}记录 {rid}: {field} = {new_val!r}")
    print("  原值已备份，可用 'undo {rid}' 还原")


def _delete(conn, record_type: str, rid: str) -> None:
    table = TABLES.get(record_type)
    if table is None:
        print(f"未知记录类型: {record_type}")
        return
    row = _get_by_id(conn, table, rid)
    if not row:
        print(f"{record_type} 记录不存在: {rid}")
        return
    _backup(conn, table, rid, row)
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (rid,))
    conn.commit()
    print(f"已删除 {TABLE_LABELS.get(table)}记录 {rid}（原值已备份，可用 'undo {rid}' 还原）")


def _status(db_path: Path, trace_code: str) -> None:
    # 复用 Web 校验逻辑，保证与前端扫码结果一致
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        import yuxi.traceability.db as d
    except ImportError:
        print("无法导入 yuxi.traceability.db，请确认在 /app 目录下运行")
        return
    d.DB_PATH = db_path
    report = d.get_trace_report(trace_code)
    if not report:
        print(f"溯源码不存在或无效: {trace_code}")
        return
    print(f"溯源码: {trace_code}")
    print(f"  批次编号: {report.batch_code}")
    print(f"  哈希校验: {'通过 ✓' if report.hash_verified else '失败 ✗'}")
    print(f"  篡改检测: {'检测到篡改！' if report.tamper_detected else '未检测到篡改'}")
    if report.tamper_detected:
        print("  → 前端扫码会显示「数据完整性校验失败 / 数据异常」")


def _undo(conn, rid: str) -> None:
    rows = conn.execute(
        "SELECT * FROM tamper_backup WHERE record_id = ? ORDER BY id DESC LIMIT 1",
        (rid,),
    ).fetchall()
    if not rows:
        print(f"没有可还原的修改记录: {rid}")
        return
    backup = rows[0]
    table = backup["record_type"]
    old = json.loads(backup["old_json"])
    if _get_by_id(conn, table, rid):
        # 记录存在 → 恢复各字段
        for k, v in old.items():
            conn.execute(f"UPDATE {table} SET {k} = ? WHERE id = ?", (v, rid))
    else:
        # 记录被删过 → 重新插入
        cols = ", ".join(old.keys())
        placeholders = ", ".join("?" for _ in old)
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(old.values()))
    conn.execute("DELETE FROM tamper_backup WHERE id = ?", (backup["id"],))
    conn.commit()
    print(f"已还原 {TABLE_LABELS.get(table)}记录 {rid}")


def _show_help() -> None:
    print(__doc__)


def _interactive(conn) -> None:
    print("番茄溯源 篡改模拟工具（开发用）—— 输入 help 查看命令，Ctrl+D 退出")
    while True:
        try:
            line = input("tamper> ").strip()
        except EOFError:
            break
        if not line:
            continue
        try:
            _run_cmd(conn, line)
        except (ValueError, sqlite3.Error) as e:
            print(f"命令执行出错: {e}")


def _run_cmd(conn, line: str) -> None:
    parts = line.split()
    cmd = parts[0]
    args = parts[1:]

    if cmd in ("list-batches", "lb"):
        _list_batches(conn)
    elif cmd in ("list-harvests", "lh"):
        _list_records(conn, "harvests", args[0])
    elif cmd in ("list-inspections", "li"):
        _list_records(conn, "inspections", args[0])
    elif cmd in ("list-environments", "le"):
        _list_records(conn, "environments", args[0])
    elif cmd in ("list-activities", "la"):
        _list_records(conn, "activities", args[0])
    elif cmd in ("modify-harvest", "mh"):
        field, value = args[1].split("=", 1)
        _modify(conn, "harvest", args[0], field, value)
    elif cmd in ("modify-inspection", "mi"):
        field, value = args[1].split("=", 1)
        _modify(conn, "inspection", args[0], field, value)
    elif cmd in ("modify-environment", "me"):
        field, value = args[1].split("=", 1)
        _modify(conn, "environment", args[0], field, value)
    elif cmd in ("modify-activity", "ma"):
        field, value = args[1].split("=", 1)
        _modify(conn, "activity", args[0], field, value)
    elif cmd in ("delete-harvest", "dh"):
        _delete(conn, "harvest", args[0])
    elif cmd in ("delete-inspection", "di"):
        _delete(conn, "inspection", args[0])
    elif cmd in ("undo", "u"):
        _undo(conn, args[0])
    elif cmd in ("help", "h", "?"):
        _show_help()
    else:
        print(f"未知命令: {cmd}（输入 help 查看可用命令）")


def main() -> None:
    parser = argparse.ArgumentParser(description="番茄溯源篡改模拟工具（开发用）")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite 数据库路径")
    parser.add_argument("command", nargs="*", help="直接执行命令（不进入交互模式）")
    args = parser.parse_args()

    db_path = Path(args.db)
    conn = _connect(db_path)

    if args.command:
        _run_cmd(conn, " ".join(args.command))
        if args.command[0] == "status":
            conn.close()
            _status(db_path, args.command[1])
    else:
        _interactive(conn)
        conn.close()


if __name__ == "__main__":
    main()
