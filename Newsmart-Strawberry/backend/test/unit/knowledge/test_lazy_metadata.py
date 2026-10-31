from types import SimpleNamespace
from unittest.mock import AsyncMock

from yuxi.knowledge.factory import KnowledgeBaseFactory
from yuxi.knowledge.manager import KnowledgeBaseManager
from yuxi.repositories.knowledge_base_repository import KnowledgeBaseRepository


async def test_database_lookup_loads_missing_metadata_once(tmp_path, monkeypatch):
    manager = KnowledgeBaseManager(str(tmp_path))
    instance = SimpleNamespace(databases_meta={})

    async def load():
        instance.databases_meta["kb_test"] = {}

    instance._load_metadata = AsyncMock(side_effect=load)
    monkeypatch.setattr(manager, "_get_or_create_kb_instance", lambda kind: instance)
    monkeypatch.setattr(KnowledgeBaseFactory, "is_type_supported", lambda kind: True)
    monkeypatch.setattr(
        KnowledgeBaseRepository, "get_by_kb_id", AsyncMock(return_value=SimpleNamespace(kb_type="qdrant"))
    )
    assert await manager._get_kb_for_database("kb_test") is instance
    assert await manager._get_kb_for_database("kb_test") is instance
    instance._load_metadata.assert_awaited_once()
