from unittest.mock import AsyncMock

import pytest

from yuxi.models.embed import OtherEmbedding


@pytest.mark.parametrize("model", ["nomic-embed-text", "nomic-embed-text:latest"])
async def test_nomic_distinguishes_documents_and_queries(model, monkeypatch):
    embed = OtherEmbedding(model=model, base_url="http://localhost/v1/embeddings", api_key="test")
    assert embed.build_payload(["草莓"])["input"] == ["search_document: 草莓"]
    assert embed.build_payload("search_query: 草莓")["input"] == "search_query: 草莓"
    encode = AsyncMock(return_value=[[1.0]])
    monkeypatch.setattr(embed, "aencode", encode)
    assert await embed.aencode_queries("草莓") == [[1.0]]
    encode.assert_awaited_once_with(["search_query: 草莓"])


def test_other_models_keep_original_payload():
    embed = OtherEmbedding(model="bge-m3", base_url="http://localhost/embeddings", api_key="test")
    assert embed.build_payload(["草莓"])["input"] == ["草莓"]
