"""Verify the imported corpus against real native Windows services."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_strawberry_corpus_persisted_and_retrievable():
    if os.getenv("TEST_NATIVE_STRAWBERRY") != "1":
        pytest.skip("Set TEST_NATIVE_STRAWBERRY=1 with native services and Ollama running")
    backend = Path(__file__).resolve().parents[2]
    code = """
import asyncio
from scripts import bootstrap_strawberry as bootstrap
from yuxi.repositories.knowledge_chunk_repository import KnowledgeChunkRepository

async def verify():
    bootstrap.pg_manager.initialize()
    try:
        rows = await bootstrap.KnowledgeBaseRepository().get_all()
        row = next(row for row in rows if row.name == bootstrap.NAME)
        kb = await bootstrap.knowledge_base._get_kb_for_database(row.kb_id)
        files = [f for f in kb.files_meta.values() if f["kb_id"] == row.kb_id]
        assert len(files) == 12, len(files)
        assert all(f["status"] == "indexed" for f in files)
        count = await KnowledgeChunkRepository().count_by_kb_id(row.kb_id)
        assert count > 0
        assert kb.client.count(row.kb_id, exact=True).count == count
        cases = [
            ("草莓灰霉病如何预防", "botrytis.md"),
            ("草莓白粉病叶片症状", "powdery-mildew.md"),
            ("草莓定植深度，根颈应该埋多深", "03-soil-and-transplanting.md"),
            ("草莓滴灌和水肥管理，如何控制EC", "04-irrigation-and-nutrition.md"),
            ("草莓蚜虫和叶螨如何防治", "07-mites-aphids-thrips.md"),
            ("草莓采收后怎么冷却和清洗", "08-harvest-storage-and-hygiene.md"),
            ("草莓育苗和匍匐茎繁殖", "02-varieties-and-propagation.md"),
        ]
        for query, expected in cases:
            hits = await kb.aquery(query, row.kb_id, search_mode="hybrid", final_top_k=5,
                                   vector_weight=0.3, bm25_weight=0.7)
            sources = [hit["metadata"]["source"] for hit in hits]
            assert expected in sources, (query, expected, sources)
            print(query, sources)
        print(f"VERIFIED files={len(files)} chunks={count} topics={len(cases)}")
    finally:
        await bootstrap.pg_manager.close()

with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
    runner.run(verify())
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=backend,
        env={**os.environ, "PYTHONUTF8": "1", "YUXI_SKIP_APP_INIT": "0"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VERIFIED files=12" in result.stdout
