import ast
from pathlib import Path

import pytest


def environment_loader():
    source = Path(__file__).resolve().parents[2] / "package/yuxi/__init__.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_load_environment"
    )
    return compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec")


def test_local_environment_never_reads_classroom_or_repository_env(tmp_path, monkeypatch):
    import os

    calls = []
    local_env = tmp_path / ".runtime/local.env"
    local_env.parent.mkdir()
    local_env.write_text("LOCAL_WINDOWS_MODE=true\n", encoding="ascii")
    monkeypatch.setenv("LOCAL_WINDOWS_MODE", "true")
    namespace = {
        "os": os, "Path": Path,
        "__file__": str(tmp_path / "backend/package/yuxi/__init__.py"),
        "load_dotenv": lambda path, **kwargs: calls.append((path, kwargs)),
    }
    exec(environment_loader(), namespace)
    namespace["_load_environment"]()
    assert calls == [(local_env, {"override": True})]


def test_local_environment_requires_service_setup(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("LOCAL_WINDOWS_MODE", "true")
    namespace = {
        "os": os, "Path": Path,
        "__file__": str(tmp_path / "backend/package/yuxi/__init__.py"),
    }
    exec(environment_loader(), namespace)
    with pytest.raises(RuntimeError, match="start-services.cmd"):
        namespace["_load_environment"]()
