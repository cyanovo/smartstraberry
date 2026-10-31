"""Import the sourced starter corpus using real embedding and graph services."""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
os.chdir(BACKEND)
os.environ["LOCAL_WINDOWS_MODE"] = "true"
sys.path.insert(0, str(BACKEND / "package"))

import yuxi  # noqa: E402,F401
from sqlalchemy import select  # noqa: E402
from yuxi.knowledge import knowledge_base  # noqa: E402
from yuxi.knowledge.graphs.milvus_graph_service import MilvusGraphService  # noqa: E402
from yuxi.models.embed import select_embedding_model  # noqa: E402
from yuxi.models.providers.cache import model_cache  # noqa: E402
from yuxi.models.providers.service import create_provider_config, get_model_provider_by_id, get_all_model_providers  # noqa: E402
from yuxi.repositories.knowledge_base_repository import KnowledgeBaseRepository  # noqa: E402
from yuxi.repositories.knowledge_chunk_repository import KnowledgeChunkRepository  # noqa: E402
from yuxi.storage.minio.client import aupload_file_to_minio  # noqa: E402
from yuxi.storage.neo4j import get_shared_neo4j_connection  # noqa: E402
from yuxi.storage.postgres.manager import pg_manager  # noqa: E402
from yuxi.storage.postgres.models_business import User  # noqa: E402

NAME = "草莓栽培与病害知识库"


async def main():
    pg_manager.initialize()
    try:
        if "--graph" in sys.argv:
            get_shared_neo4j_connection().driver.verify_connectivity()
        async with pg_manager.get_async_session_context() as session:
            owner = (await session.execute(select(User).where(User.role == "superadmin"))).scalars().first()
        if owner is None:
            raise RuntimeError("Create a superadmin through the application's normal setup first")
        async with pg_manager.get_async_session_context() as session:
            if not await get_model_provider_by_id(session, "local-ollama"):
                await create_provider_config(
                    session,
                    {
                        "provider_id": "local-ollama",
                        "display_name": "本地 Ollama",
                        "provider_type": "openai",
                        "base_url": "http://127.0.0.1:11434/v1",
                        "embedding_base_url": "http://127.0.0.1:11434/v1/embeddings",
                        "api_key": "ollama",
                        "capabilities": ["embedding", "chat"],
                        "is_enabled": True,
                        "enabled_models": [
                            {"id": "nomic-embed-text:latest", "type": "embedding", "dimension": 768, "batch_size": 8},
                            {"id": "qwen2.5:1.5b", "type": "chat"},
                        ],
                    },
                    owner.uid,
                )
            model_cache.rebuild(await get_all_model_providers(session))
        rows = await KnowledgeBaseRepository().get_all()
        existing = next((row for row in rows if row.name == NAME), None)
        embedding_spec = existing.embedding_model_spec if existing else "local-ollama:nomic-embed-text:latest"
        chat_models = model_cache.get_all_specs("chat")
        if not chat_models:
            raise RuntimeError("Configure an LLM in the application's model settings first")
        chat_spec = existing.llm_model_spec if existing else "local-ollama:qwen2.5:1.5b"
        vector = (await select_embedding_model(embedding_spec).abatch_encode(["草莓灰霉病如何预防？"]))[0]
        print(f"Embedding verified: {embedding_spec}, dimension={len(vector)}", flush=True)
        if existing:
            kb_id = existing.kb_id
        else:
            info = await knowledge_base.create_database(
                NAME,
                "草莓全流程种植基础库：品种、育苗、定植、水肥、花果、病虫害、采后及巡检。公开推广资料中文整理，参数须本地化核验。",
                kb_type="qdrant",
                embedding_model_spec=embedding_spec,
                llm_model_spec=chat_spec,
                created_by=owner.uid,
                share_config={"access_level": "global", "department_ids": [], "user_uids": []},
            )
            kb_id = info["kb_id"]
        kb = await knowledge_base._get_kb_for_database(kb_id)
        kb.databases_meta[kb_id]["query_params"]["options"].update(
            search_mode="hybrid", vector_weight=0.3, bm25_weight=0.7, final_top_k=5
        )
        await kb._persist_kb(kb_id)
        for path in sorted((BACKEND.parent / "data" / "strawberry-knowledge").glob("*.md")):
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            matching = next(
                (f for f in kb.files_meta.values() if f.get("kb_id") == kb_id and f.get("content_hash") == digest), None
            )
            if matching is None:
                url = await aupload_file_to_minio("knowledgebases", f"{kb_id}/sources/{digest}/{path.name}", data)
                matching = await kb.add_file_record(
                    kb_id, url, {"content_hashes": {url: digest}, "file_sizes": {url: len(data)}}, owner.uid
                )
            file_id = matching["file_id"]
            if matching["status"] in {"uploaded", "error_parsing"}:
                matching = await kb.parse_file(kb_id, file_id, owner.uid)
            if matching["status"] != "indexed":
                matching = await kb.index_file(kb_id, file_id, owner.uid)
            if matching["status"] != "indexed":
                raise RuntimeError(f"Import failed: {path.name}, status={matching['status']}")
            print(f"Indexed {path.name}", flush=True)
        for mode in ("vector", "keyword", "hybrid"):
            hits = await kb.aquery("草莓灰霉病如何预防", kb_id, search_mode=mode, final_top_k=3)
            if not hits:
                raise RuntimeError(f"No results for {mode}")
            print(f"Retrieval {mode}: {len(hits)} hits; source={hits[0]['metadata']['source']}", flush=True)
        print("Knowledge base imported:", kb_id, flush=True)
        count = await KnowledgeChunkRepository().count_by_kb_id(kb_id)
        vector_count = kb.client.count(kb_id, exact=True).count
        if count != vector_count:
            raise RuntimeError(f"PostgreSQL/Qdrant chunk mismatch: {count}/{vector_count}")
        print(f"Persisted chunks: {count}", flush=True)
        if "--graph" not in sys.argv:
            return
        graph = MilvusGraphService()
        await graph.configure(
            kb_id,
            "llm",
            {
                "model_spec": chat_spec,
                "concurrency_count": 1,
                "schema": (
                    "只抽取正文明确支持的草莓、病害、病原、症状、环境条件与管理措施关系。"
                    "保留可能性，不把风险因素写成确诊。不要抽取网页地址、日期和机构。"
                    "实体及关系使用中文，病原学名保留拉丁文。"
                ),
            },
            owner.uid,
        )
        result = await graph.build_pending_chunks(kb_id, batch_size=10)
        print("Graph build:", json.dumps(result, ensure_ascii=False), flush=True)
        if result["failed"] or result["remaining"]:
            raise RuntimeError("Graph import is incomplete; fix provider configuration then rerun")
        for mode in ("vector", "keyword", "hybrid"):
            hits = await kb.aquery("草莓灰霉病如何预防", kb_id, search_mode=mode, final_top_k=3)
            if not hits:
                raise RuntimeError(f"No results for {mode}")
            print(f"Retrieval {mode}: {len(hits)} hits; source={hits[0]['metadata']['source']}", flush=True)
        status = await graph.get_status(kb_id)
        print("Knowledge base:", kb_id, json.dumps(status, ensure_ascii=False), flush=True)
    finally:
        await pg_manager.close()


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(main())
