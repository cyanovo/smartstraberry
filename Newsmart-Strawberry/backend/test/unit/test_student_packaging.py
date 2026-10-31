"""Teacher-side packaging boundaries; no services or archive writes."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def update_builder():
    path = Path(__file__).resolve().parents[4] / "packaging/build_update.py"
    spec = importlib.util.spec_from_file_location("student_update_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", [
    "Newsmart-Strawberry/.runtime/local.env",
    "Newsmart-Strawberry/backend/saves/field-work/model.pt",
    "Newsmart-Strawberry/backend/.venv/pyvenv.cfg",
    "Newsmart-Strawberry/web/node_modules/package.json",
    "strawberry_vision/weights/yolo26n.pt",
    "strawberry_vision/dataset_maturity/manifest.csv",
    "strawberry_project/output/report.json",
    "backup/business.dump",
    "LOGIN.txt",
    "student-version.json",
    "Newsmart-Strawberry/web/src/../../.runtime/config.json",
    "D:/outside/file.py",
])
def test_update_excludes_student_state(update_builder, path):
    assert not update_builder.allowed(path)


@pytest.mark.parametrize("path", [
    "Newsmart-Strawberry/backend/server/routers/album_router.py",
    "Newsmart-Strawberry/web/src/views/AlbumsView.vue",
    "Newsmart-Strawberry/scripts/windows/services.ps1",
    "AGENT_DEPLOY.md",
    "deploy.py",
])
def test_update_includes_code_and_instructions(update_builder, path):
    assert update_builder.allowed(path)


def test_validation_launcher_path_roundtrip():
    source = r"D:\teacher"
    validation = source + r"\delivery\student"
    student = r"E:\StrawberryStudent"
    launcher = validation + r"\Newsmart-Strawberry\web\node_modules\vite\bin\vite.js"
    packaged = launcher.replace(validation, source)
    relocated = packaged.replace(source, student)
    assert relocated == student + r"\Newsmart-Strawberry\web\node_modules\vite\bin\vite.js"
