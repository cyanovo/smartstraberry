from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from qdrant_client import QdrantClient, models

from yuxi.knowledge.implementations.qdrant import QdrantKB, point_id, sparse_text


@pytest.fixture
def kb(tmp_path, monkeypatch):
    from yuxi.knowledge.implementations import qdrant

    instance = QdrantKB(str(tmp_path))
    instance.client.close()
    instance.client = QdrantClient(":memory:")
    instance.databases_meta = {"kb_test": {"embedding_model_spec": "test:embedding"}}
    monkeypatch.setattr(
        qdrant.model_cache, "get_model_info", lambda spec: SimpleNamespace(model_type="embedding", dimension=3)
    )
    monkeypatch.setattr(instance, "_get_embedding_function", lambda spec: AsyncMock(return_value=[[1.0, 0.0, 0.0]]))
    instance.files_meta = {
        "f1": {"kb_id": "kb_test", "filename": "草莓病害.md"},
        "f2": {"kb_id": "kb_test", "filename": "灌溉.md"},
    }
    instance._ensure_collection("kb_test", 3)
    instance.client.upsert(
        "kb_test",
        [
            models.PointStruct(
                id=point_id("c1"),
                vector={"dense": [1.0, 0.0, 0.0], "text": sparse_text("草莓灰霉病 通风")},
                payload={"chunk_id": "c1", "file_id": "f1", "content": "草莓灰霉病 通风", "chunk_index": 0},
            ),
            models.PointStruct(
                id=point_id("c2"),
                vector={"dense": [0.0, 1.0, 0.0], "text": sparse_text("滴灌 土壤水分")},
                payload={"chunk_id": "c2", "file_id": "f2", "content": "滴灌 土壤水分", "chunk_index": 0},
            ),
        ],
    )
    yield instance
    instance.client.close()


def test_sparse_text_is_stable_and_chinese_aware():
    one = sparse_text("草莓 灰霉病")
    assert one == sparse_text("草莓 灰霉病")
    assert one.indices and len(set(one.indices)) == len(one.indices)
    assert set(sparse_text("灰霉病", query=True).indices) <= set(one.indices)
    assert sparse_text("?!").indices == []


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
async def test_retrieval_returns_source_and_respects_file_filter(kb, mode):
    results = await kb.aquery("灰霉病", "kb_test", search_mode=mode, final_top_k=1)
    assert results[0]["metadata"] == {"chunk_id": "c1", "file_id": "f1", "chunk_index": 0, "source": "草莓病害.md"}
    assert results[0]["score"] > 0
    assert await kb.aquery("灰霉病", "kb_test", search_mode=mode, file_name="missing") == []


async def test_delete_only_target_file(kb):
    await kb._delete_file_chunks_from_milvus("kb_test", "f1")
    assert kb.client.count("kb_test").count == 1
    assert kb.client.retrieve("kb_test", [point_id("c2")])[0].payload["file_id"] == "f2"


def test_dimension_mismatch_does_not_destroy_data(kb):
    with pytest.raises(ValueError, match="dimension changed"):
        kb._ensure_collection("kb_test", 4)
    assert kb.client.count("kb_test").count == 2


def test_zero_weight_excludes_ranking():
    hit = {"metadata": {"chunk_id": "c1"}, "score": 1}
    assert QdrantKB._weighted_rrf([([hit], 0)]) == []


async def test_unknown_mode_fails(kb):
    with pytest.raises(ValueError, match="Unknown search mode"):
        await kb.aquery("query", "kb_test", search_mode="invalid")
