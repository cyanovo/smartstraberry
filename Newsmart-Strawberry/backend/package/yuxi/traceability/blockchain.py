"""
番茄溯源区块链 —— 区块链保证溯源数据不可篡改
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

# Docker 卷路径：/app/saves 对应 docker/volumes/greenhouse
_SAVES_DIR = (
    Path("/app/saves")
    if Path("/app/saves").exists()
    else Path(__file__).resolve().parent.parent.parent.parent / "docker" / "volumes" / "greenhouse"
)
_SAVES_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _SAVES_DIR / ".tomato_blockchain.json"

_state: dict[str, Any] = {"chain": []}


def _uses_postgres() -> bool:
    return os.getenv("TRACE_DATABASE_BACKEND", "sqlite").strip().lower() == "postgres"


def _row_to_block(row) -> dict[str, Any]:
    return {
        "index": row["block_index"],
        "timestamp": row["timestamp"],
        "data": json.loads(row["data_json"]),
        "previous_hash": row["previous_hash"],
        "hash": row["hash"],
        "nonce": row["nonce"],
    }


def _load():
    global _state
    if _uses_postgres():
        return
    if DB_PATH.exists():
        try:
            _state = json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            _state = {"chain": []}


def _save():
    if _uses_postgres():
        return
    DB_PATH.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash(record: dict[str, Any]) -> str:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def calculate_hash(block: dict[str, Any]) -> str:
    return _hash(
        {
            "index": block["index"],
            "timestamp": block["timestamp"],
            "data": block["data"],
            "previous_hash": block["previous_hash"],
            "nonce": block["nonce"],
        }
    )


def proof_of_work(block_data: dict[str, Any], difficulty: int = 4) -> tuple:
    """工作量证明：前 difficulty 位为 0"""
    prefix = "0" * difficulty
    nonce = 0
    while True:
        block_data["nonce"] = nonce
        h = calculate_hash(block_data)
        if h.startswith(prefix):
            return h, nonce
        nonce += 1


def create_genesis_block() -> dict[str, Any]:
    block = {
        "index": 0,
        "timestamp": time.time(),
        "data": {"event": "创世区块 - 番茄溯源链", "record_id": "GENESIS"},
        "previous_hash": "0" * 64,
        "nonce": 0,
    }
    h, nonce = proof_of_work(block)
    block["hash"] = h
    block["nonce"] = nonce
    return block


def add_block(data: dict[str, Any]) -> dict[str, Any]:
    """将番茄溯源数据写入区块链"""
    if _uses_postgres():
        from yuxi.traceability import db

        conn = db._get_conn()
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(?))", ("traceability-chain",))
        rows = conn.execute("SELECT * FROM trace_blocks ORDER BY block_index").fetchall()
        chain = [_row_to_block(row) for row in rows]
        if not chain:
            genesis = create_genesis_block()
            conn.execute(
                """
                INSERT INTO trace_blocks
                    (block_index, timestamp, data_json, previous_hash, hash, nonce)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    genesis["index"],
                    genesis["timestamp"],
                    json.dumps(genesis["data"], ensure_ascii=False),
                    genesis["previous_hash"],
                    genesis["hash"],
                    genesis["nonce"],
                ),
            )
            chain = [genesis]

        prev = chain[-1]
        block = {
            "index": prev["index"] + 1,
            "timestamp": time.time(),
            "data": data,
            "previous_hash": prev["hash"],
            "nonce": 0,
        }
        block["hash"], block["nonce"] = proof_of_work(block)
        conn.execute(
            """
            INSERT INTO trace_blocks
                (block_index, timestamp, data_json, previous_hash, hash, nonce)
            VALUES (?,?,?,?,?,?)
            """,
            (
                block["index"],
                block["timestamp"],
                json.dumps(block["data"], ensure_ascii=False),
                block["previous_hash"],
                block["hash"],
                block["nonce"],
            ),
        )
        conn.commit()
        conn.close()
        return block

    _load()
    chain = _state.get("chain", [])
    if not chain:
        chain = [create_genesis_block()]

    prev = chain[-1]
    block = {
        "index": prev["index"] + 1,
        "timestamp": time.time(),
        "data": data,
        "previous_hash": prev["hash"],
        "nonce": 0,
    }
    h, nonce = proof_of_work(block)
    block["hash"] = h
    block["nonce"] = nonce
    chain.append(block)
    _state["chain"] = chain
    _save()
    return block


def get_chain() -> list[dict[str, Any]]:
    if _uses_postgres():
        from yuxi.traceability import db

        conn = db._get_conn()
        rows = conn.execute("SELECT * FROM trace_blocks ORDER BY block_index").fetchall()
        conn.close()
        return [_row_to_block(row) for row in rows]

    _load()
    chain = _state.get("chain", [])
    if not chain:
        return []
    return [
        {
            "index": b["index"],
            "timestamp": b["timestamp"],
            "data": b["data"],
            "previous_hash": b["previous_hash"],
            "hash": b["hash"],
            "nonce": b["nonce"],
        }
        for b in chain
    ]


def verify_chain() -> dict[str, Any]:
    """验证区块链完整性"""
    if _uses_postgres():
        chain = get_chain()
    else:
        _load()
        chain = _state.get("chain", [])
    if not chain:
        return {"valid": True, "details": [], "message": "链为空"}

    details = []
    all_valid = True
    for i in range(len(chain)):
        block = chain[i]
        recalc = calculate_hash(block)
        hash_ok = recalc == block["hash"]
        prev_ok = True
        if i > 0:
            prev_ok = block["previous_hash"] == chain[i - 1]["hash"]

        if not hash_ok or not prev_ok:
            all_valid = False
        details.append(
            {
                "index": block["index"],
                "hash_match": hash_ok,
                "prev_match": prev_ok,
                "stored_hash": block["hash"][:24] + "...",
                "recalculated_hash": recalc[:24] + "...",
            }
        )

    return {
        "valid": all_valid,
        "details": details,
        "message": "所有区块哈希一致，链完整 ✓" if all_valid else "发现哈希不匹配！数据可能已被篡改！",
    }


def get_block_count() -> int:
    if _uses_postgres():
        return len(get_chain())
    _load()
    return len(_state.get("chain", []))


def reset_chain():
    global _state
    if _uses_postgres():
        from yuxi.traceability import db

        conn = db._get_conn()
        conn.execute("DELETE FROM trace_blocks")
        conn.commit()
        conn.close()
        return

    _state = {"chain": []}
    if DB_PATH.exists():
        DB_PATH.unlink()


# 启动时加载
_load()
