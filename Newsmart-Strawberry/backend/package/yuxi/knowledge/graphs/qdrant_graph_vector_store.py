import asyncio
import os

from qdrant_client import QdrantClient, models

from yuxi.knowledge.graphs.graph_utils import graph_entity_collection_name, graph_triple_collection_name
from yuxi.knowledge.implementations.qdrant import point_id
from yuxi.models.embed import select_embedding_model
from yuxi.models.providers.cache import model_cache


class QdrantGraphVectorStore:
    def __init__(self):
        self.client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://127.0.0.1:16333"), timeout=60)

    async def insert_missing_graph_records(self, *, kb_id, embedding_model_spec, entities, triples):
        info = model_cache.get_model_info(embedding_model_spec)
        if not info or not info.dimension:
            raise ValueError("Graph indexing requires a configured embedding dimension")
        embed = select_embedding_model(embedding_model_spec)
        groups = [
            (graph_entity_collection_name(kb_id), entities, "entity_id"),
            (graph_triple_collection_name(kb_id), triples, "triple_id"),
        ]
        for name, records, key in groups:
            if not records:
                continue
            if not await asyncio.to_thread(self.client.collection_exists, name):
                await asyncio.to_thread(
                    self.client.create_collection,
                    name,
                    vectors_config=models.VectorParams(size=info.dimension, distance=models.Distance.COSINE),
                )
            for start in range(0, len(records), 128):
                batch = records[start : start + 128]
                found = await asyncio.to_thread(self.client.retrieve, name, [point_id(row[key]) for row in batch])
                existing = {str(point.id) for point in found}
                missing = [row for row in batch if point_id(row[key]) not in existing]
                if not missing:
                    continue
                vectors = await embed.abatch_encode([row["content"] for row in missing])
                points = [
                    models.PointStruct(
                        id=point_id(row[key]),
                        vector=vector,
                        payload={
                            "id": row[key],
                            "content": row["content"],
                            "source_id": row.get("source_entity_id"),
                            "target_id": row.get("target_entity_id"),
                        },
                    )
                    for row, vector in zip(missing, vectors, strict=True)
                ]
                await asyncio.to_thread(self.client.upsert, name, points, wait=True)

    async def _search(self, name, query_text, embedding_model_spec, top_k):
        if top_k <= 0 or not await asyncio.to_thread(self.client.collection_exists, name):
            return []
        vector = (await select_embedding_model(embedding_model_spec).aencode_queries([query_text]))[0]
        response = await asyncio.to_thread(self.client.query_points, name, query=vector, limit=top_k, with_payload=True)
        return [{**hit.payload, "score": hit.score} for hit in response.points]

    async def search_entities(self, *, kb_id, query_text, embedding_model_spec, top_k):
        return await self._search(graph_entity_collection_name(kb_id), query_text, embedding_model_spec, top_k)

    async def search_triples(self, *, kb_id, query_text, embedding_model_spec, top_k):
        return await self._search(graph_triple_collection_name(kb_id), query_text, embedding_model_spec, top_k)

    async def delete_graph_records(self, kb_id, *, entity_ids, triple_ids):
        for name, ids in [
            (graph_entity_collection_name(kb_id), entity_ids),
            (graph_triple_collection_name(kb_id), triple_ids),
        ]:
            if ids and await asyncio.to_thread(self.client.collection_exists, name):
                await asyncio.to_thread(self.client.delete, name, [point_id(value) for value in ids], wait=True)

    def drop_graph_collections(self, kb_id):
        for name in (graph_entity_collection_name(kb_id), graph_triple_collection_name(kb_id)):
            if self.client.collection_exists(name):
                self.client.delete_collection(name)
