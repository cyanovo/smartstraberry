import pytest

from yuxi.agents.toolkits.iot.album_tools import analyze_strawberry_album
from yuxi.agents.toolkits.service import _extract_tool_info
from yuxi.agents.toolkits.utils import get_tool_info


@pytest.mark.parametrize("extract", [_extract_tool_info, lambda tool: get_tool_info([tool])[0]])
def test_album_metadata_excludes_injected_runtime(extract):
    info = extract(analyze_strawberry_album)
    assert {arg["name"] for arg in info["args"]} == {
        "album_id", "kb_id", "average_mass_g", "disease_record_ids"
    }


def test_metadata_cache_is_not_published_after_failure(monkeypatch):
    from yuxi.agents.toolkits import registry, service

    monkeypatch.setattr(service, "_metadata_cache", [])
    monkeypatch.setattr(registry, "get_all_tool_instances", lambda: [analyze_strawberry_album] * 2)
    original = service._extract_tool_info
    calls = 0

    def fail_second(tool):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("schema failure")
        return original(tool)

    monkeypatch.setattr(service, "_extract_tool_info", fail_second)
    with pytest.raises(ValueError, match="schema failure"):
        service.get_tool_metadata()
    assert service._metadata_cache == []


def test_all_registered_tools_have_serializable_metadata(monkeypatch):
    from yuxi.agents.toolkits import registry, service

    monkeypatch.setattr(service, "_metadata_cache", [])
    metadata = service.get_tool_metadata()
    assert {item["slug"] for item in metadata} == {
        tool.name for tool in registry.get_all_tool_instances()
    }
    assert service.get_tool_metadata() is metadata
