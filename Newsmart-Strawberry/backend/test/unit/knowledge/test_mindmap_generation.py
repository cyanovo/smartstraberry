import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from yuxi.knowledge.utils import mindmap_utils as module


@pytest.mark.parametrize("native", [False, True])
async def test_mindmap_uses_kb_model_and_indexed_content(monkeypatch, httpx_mock, native):
    monkeypatch.setattr(
        module.knowledge_base,
        "get_database_info",
        AsyncMock(
            return_value={
                "name": "草莓",
                "llm_model_spec": "local-ollama:qwen2.5:1.5b",
                "files": {"f1": {"filename": "planting.md", "type": "md"}},
            }
        ),
    )
    monkeypatch.setattr(
        module.KnowledgeChunkRepository,
        "list_by_file_id",
        AsyncMock(return_value=[SimpleNamespace(content="定植时根颈不能深埋")]),
    )
    model = SimpleNamespace(
        model_params={},
        call=AsyncMock(return_value=SimpleNamespace(content='{"content":"草莓","children":[]}')),
        client=SimpleNamespace(close=AsyncMock()),
    )
    selected = []
    monkeypatch.setattr(
        module.model_cache,
        "get_model_info",
        lambda spec: (
            SimpleNamespace(provider_id="local-ollama", model_id="qwen2.5:1.5b", base_url="http://localhost:11434/v1")
            if native
            else None
        ),
    )
    if native:
        httpx_mock.add_response(
            url="http://localhost:11434/api/chat",
            json={
                "message": {"content": '{"content":"草莓","children":[]}'},
            },
        )
    monkeypatch.setattr(module, "select_model", lambda model_spec: selected.append(model_spec) or model)
    update = AsyncMock()
    monkeypatch.setattr(module.KnowledgeBaseRepository, "update", update)
    result = await module.generate_database_mindmap("kb_test")
    assert selected == ["local-ollama:qwen2.5:1.5b"]
    if native:
        payload = json.loads(httpx_mock.get_request().content)
        assert payload["options"]["num_ctx"] == 16384
        assert "定植时根颈不能深埋" in payload["messages"][1]["content"]
    else:
        assert "定植时根颈不能深埋" in model.call.call_args.args[0][1]["content"]
    update.assert_awaited_once_with("kb_test", {"mindmap": result["mindmap"]})
    model.client.close.assert_awaited_once()


def test_mindmap_rejects_invalid_child():
    with pytest.raises(ValueError, match="children"):
        module.parse_mindmap_content('{"content":"root","children":[{"content":"bad"}]}')


def test_mindmap_rejects_non_string_label():
    with pytest.raises(ValueError, match="content"):
        module.parse_mindmap_content('{"content":"root","children":[{"content":[],"children":[]}]}')


def test_mindmap_rejects_duplicate_branches():
    with pytest.raises(ValueError, match="重复"):
        module.parse_mindmap_content(
            '{"content":"root","children":[{"content":"a","children":[]},{"content":"a","children":[]}]}'
        )
