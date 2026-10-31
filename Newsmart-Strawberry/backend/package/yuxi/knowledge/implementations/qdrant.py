"""Qdrant storage using the existing document lifecycle and PostgreSQL metadata."""

import asyncio
import hashlib
import os
from collections import Counter
from uuid import NAMESPACE_URL, uuid5

import jieba
from qdrant_client import QdrantClient, models

from yuxi.knowledge.base import KnowledgeBase
from yuxi.knowledge.implementations.milvus import MilvusKB, _retrieval_config_options
from yuxi.models.providers.cache import model_cache
from yuxi.repositories.knowledge_chunk_repository import KnowledgeChunkRepository


def point_id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, value))


def sparse_text(text: str, *, query: bool = False) -> models.SparseVector:
    # Fixed length normalization keeps updates independent of corpus rewrites.
    # Qdrant supplies corpus IDF; jieba provides Chinese token boundaries.
    counts = Counter(token.lower() for token in jieba.cut(text) if token.strip() and token.isalnum())
    length = sum(counts.values())
    values = {}
    for token, frequency in counts.items():
        index = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big")
        weight = 1.0 if query else frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / 256))
        values[index] = values.get(index, 0.0) + weight
    indices = sorted(values)
    return models.SparseVector(indices=indices, values=[values[index] for index in indices])


class QdrantKB(MilvusKB):
    kb_type = "qdrant"
    name = "Qdrant"
    description = "Windows 原生向量知识库，支持中文稀疏检索、混合检索与 Neo4j 图谱"

    def __init__(self, work_dir: str, **kwargs):
        KnowledgeBase.__init__(self, work_dir)
        self._metadata_lock = asyncio.Lock()
        self.collections = {}
        self.client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://127.0.0.1:16333"), timeout=60)

    async def _create_kb_instance(self, kb_id: str, kb_config: dict):
        metadata = self.databases_meta[kb_id]
        spec = metadata.get("embedding_model_spec")
        info = model_cache.get_model_info(spec)
        if not info or info.model_type != "embedding" or not info.dimension:
            raise ValueError(f"Embedding model with an explicit dimension is required: {spec}")
        await asyncio.to_thread(self._ensure_collection, kb_id, info.dimension)
        return kb_id

    def _ensure_collection(self, name: str, dimension: int):
        if self.client.collection_exists(name):
            vectors = self.client.get_collection(name).config.params.vectors
            if not isinstance(vectors, dict) or not vectors.get("dense") or vectors["dense"].size != dimension:
                raise ValueError("Embedding dimension changed; create a new knowledge base")
            return
        self.client.create_collection(
            name,
            vectors_config={"dense": models.VectorParams(size=dimension, distance=models.Distance.COSINE)},
            sparse_vectors_config={"text": models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )

    async def _initialize_kb_instance(self, instance):
        return None

    async def _get_milvus_collection(self, kb_id: str):
        # Legacy lifecycle hook name; the returned handle is a Qdrant collection name.
        if kb_id not in self.collections:
            self.collections[kb_id] = await self._create_kb_instance(kb_id, {})
        return self.collections[kb_id]

    async def _insert_chunks_to_stores(self, kb_id, file_id, collection, chunks, embeddings):
        if len(chunks) != len(embeddings):
            raise ValueError("Embedding response count does not match chunk count")
        points = [
            models.PointStruct(
                id=point_id(chunk["id"]),
                vector={"dense": vector, "text": sparse_text(chunk["content"])},
                payload={key: chunk[key] for key in ("id", "content", "chunk_id", "file_id", "chunk_index")},
            )
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ]
        repo = KnowledgeChunkRepository()
        try:
            await asyncio.to_thread(self.client.upsert, collection, points, wait=True)
            await repo.batch_upsert(self._build_chunk_pg_records(kb_id, chunks))
        except Exception:
            await self._delete_file_chunks_from_milvus(collection, file_id)
            await repo.delete_by_file_id(file_id)
            raise

    async def _delete_file_chunks_from_milvus(self, collection, file_id):
        selector = models.Filter(must=[models.FieldCondition(key="file_id", match=models.MatchValue(value=file_id))])
        await asyncio.to_thread(self.client.delete, collection, selector, wait=True)

    async def delete_file_chunks_only(self, kb_id, file_id):
        repo = KnowledgeChunkRepository()
        if await repo.count_graph_indexed_by_file_id(file_id):
            from yuxi.knowledge.graphs.milvus_graph_service import MilvusGraphService

            await MilvusGraphService().delete_file_graph(kb_id, file_id)
        collection = await self._get_milvus_collection(kb_id)
        await self._delete_file_chunks_from_milvus(collection, file_id)
        await repo.delete_by_file_id(file_id)

    async def aquery(self, query_text, kb_id, agent_call=False, **kwargs):
        collection = await self._get_milvus_collection(kb_id)
        params = {**self._get_query_params(kb_id), **kwargs}
        mode = params.get("search_mode", "vector")
        if mode not in {"vector", "keyword", "hybrid"}:
            raise ValueError(f"Unknown search mode: {mode}")
        top_k = max(1, min(int(params.get("final_top_k", 10)), 100))
        recall = max(top_k, min(int(params.get("recall_top_k", 50)), 200))
        file_filter = None
        if params.get("file_name"):
            pattern = params["file_name"].replace("%", "")
            ids = [
                fid
                for fid, meta in self.files_meta.items()
                if meta.get("kb_id") == kb_id and pattern in meta.get("filename", "")
            ]
            if not ids:
                return []
            file_filter = models.Filter(must=[models.FieldCondition(key="file_id", match=models.MatchAny(any=ids))])

        async def search(query, using, limit):
            response = await asyncio.to_thread(
                self.client.query_points,
                collection,
                query=query,
                using=using,
                query_filter=file_filter,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "content": hit.payload["content"],
                    "score": hit.score,
                    "metadata": {
                        "chunk_id": hit.payload["chunk_id"],
                        "file_id": hit.payload["file_id"],
                        "chunk_index": hit.payload["chunk_index"],
                        "source": self._get_filename_for_file_id(hit.payload["file_id"]),
                    },
                }
                for hit in response.points
            ]

        dense, keyword = [], []
        if mode != "keyword":
            embed = self._get_embedding_function(self.databases_meta[kb_id]["embedding_model_spec"])
            embedding_query = query_text
            if self.databases_meta[kb_id]["embedding_model_spec"].endswith(
                (":nomic-embed-text", ":nomic-embed-text:latest")
            ):
                embedding_query = "search_query: " + query_text
            vector = (await embed([embedding_query]))[0]
            dense = await search(vector, "dense", recall)
            dense = [hit for hit in dense if hit["score"] >= float(params.get("similarity_threshold", 0))]
        if mode != "vector":
            sparse = sparse_text(query_text, query=True)
            if sparse.indices:
                keyword = await search(sparse, "text", max(1, min(int(params.get("bm25_top_k", 50)), 200)))
        results = dense if mode == "vector" else keyword
        if mode == "hybrid":
            results = self._weighted_rrf(
                [
                    (dense, max(0, float(params.get("vector_weight", 0.7)))),
                    (keyword, max(0, float(params.get("bm25_weight", 0.3)))),
                ]
            )
        if params.get("use_graph_retrieval"):
            graph = await self._retrieve_graph_chunks(query_text, kb_id, results, params)
            results = self._weighted_rrf([(results, 1), (graph, max(0, float(params.get("graph_weight", 1))))])
        if params.get("use_reranker") and results:
            from yuxi.models.rerank import get_reranker

            if not params.get("reranker_model"):
                raise ValueError("Select a reranker model before enabling reranking")
            reranker = get_reranker(params["reranker_model"])
            try:
                scores = await reranker.acompute_score(
                    [query_text, [item["content"] for item in results]], normalize=True
                )
                for item, score in zip(results, scores, strict=True):
                    item["rerank_score"] = float(score)
                results.sort(key=lambda item: item["rerank_score"], reverse=True)
            finally:
                await reranker.aclose()
        return results[:top_k]

    @staticmethod
    def _weighted_rrf(rankings):
        merged = {}
        for hits, weight in rankings:
            if weight <= 0:
                continue
            for rank, hit in enumerate(hits, 1):
                key = hit["metadata"]["chunk_id"]
                item = merged.setdefault(key, {**hit, "score": 0.0})
                item["score"] += weight / (60 + rank)
        return sorted(merged.values(), key=lambda hit: hit["score"], reverse=True)

    async def delete_database(self, kb_id):
        from yuxi.knowledge.graphs.milvus_graph_service import MilvusGraphService

        if await KnowledgeChunkRepository().count_graph_indexed_by_kb_id(kb_id):
            await asyncio.to_thread(MilvusGraphService().delete_graph, kb_id)
        if await asyncio.to_thread(self.client.collection_exists, kb_id):
            await asyncio.to_thread(self.client.delete_collection, kb_id)
        self.collections.pop(kb_id, None)
        return await KnowledgeBase.delete_database(self, kb_id)

    def get_query_params_config(self, kb_id, **kwargs):
        options = [item for item in _retrieval_config_options() if item["key"] != "bm25_drop_ratio_search"]
        for item in options:
            if item["key"] == "search_mode":
                item["options"] = [
                    {"value": "vector", "label": "向量检索"},
                    {"value": "keyword", "label": "中文稀疏检索"},
                    {"value": "hybrid", "label": "混合检索（RRF）"},
                ]
            item["description"] = (
                item.get("description", "").replace("Milvus BM25", "Qdrant 中文稀疏").replace("Milvus", "Qdrant")
            )
        return {"type": self.kb_type, "options": options}
