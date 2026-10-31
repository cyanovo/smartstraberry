"""Create a source-only share archive without copying local runtime state."""

import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "delivery" / "Strawberry-All-Source-2026-10-31.zip"
PREFIX = "Strawberry-All-Source"
RELEASE = ROOT / "delivery" / "Strawberry-Student-Windows-2026-10-26.zip"
RELEASE_PREFIX = "Strawberry-Student-Windows-2026-10-26"
RELEASE_OVERRIDE = "Newsmart-Strawberry/backend/package/yuxi/services/iot_service.py"
DIRECTORIES = (
    "Newsmart-Strawberry/backend",
    "Newsmart-Strawberry/web",
    "Newsmart-Strawberry/scripts/windows",
    "Newsmart-Strawberry/skills",
    "Newsmart-Strawberry/docs",
    "Newsmart-Strawberry/docker",
    "Newsmart-Strawberry/esp32",
    "Newsmart-Strawberry/strawberry_detector",
    "strawberry_project",
    "strawberry_vision",
)
ROOT_FILES = (
    "Newsmart-Strawberry/AGENTS.md",
    "Newsmart-Strawberry/ARCHITECTURE.md",
    "Newsmart-Strawberry/LICENSE",
    "Newsmart-Strawberry/README.md",
    "Newsmart-Strawberry/docker-compose.yml",
    "Newsmart-Strawberry/docker-compose.prod.yml",
    "Newsmart-Strawberry/docker-compose.registry.yml",
    "Newsmart-Strawberry/Makefile",
    "Newsmart-Strawberry/check-services.cmd",
    "Newsmart-Strawberry/setup-mqtt-lan.cmd",
    "Newsmart-Strawberry/setup-services.cmd",
    "Newsmart-Strawberry/start-services.cmd",
    "Newsmart-Strawberry/start-worker.cmd",
    "Newsmart-Strawberry/stop-services.cmd",
)
SKIP_DIRS = {
    ".git", ".idea", ".vscode", ".venv", ".venv_new", "__pycache__",
    ".pytest_cache", ".ruff_cache", ".run", ".runtime", "node_modules",
    "dist", "build", "saves", "images", "output", "downloads", "runs",
    "weights", "dataset", "datasets", "dataset_disease", "dataset_maturity",
    "annotation_review_v01", "data", "logs", "coverage", ".cache", "vibe",
}
SKIP_FILES = {"classroom.env", "annotations_draft.json"}
SKIP_SUFFIXES = {
    ".pt", ".pth", ".onnx", ".engine", ".zip", ".rar", ".7z", ".dump",
    ".db", ".sqlite", ".sqlite3", ".pem", ".p12", ".pfx", ".key",
    ".log", ".pyc", ".docx", ".pptx", ".pdf",
}
SECRET = re.compile(
    rb"(?i)(?:(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}|(?-i:AKIA[0-9A-Z]{16})|"
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"]"
    rb"(?!\$\{|<|your[_ -]|example|changeme|test|dummy|placeholder)"
    rb"[A-Za-z0-9_-]{24,}['\"])"
)
TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".vue", ".json", ".yaml", ".yml", ".md",
    ".txt", ".ps1", ".cmd", ".bat", ".toml", ".env", ".html", ".css",
    ".less", ".sh", ".xml", ".sql",
}


def included(path):
    relative = path.relative_to(ROOT)
    if path.is_symlink() or path.is_junction():
        raise RuntimeError(f"Linked file is not safe to package: {relative}")
    if any(part in SKIP_DIRS for part in relative.parts[:-1]):
        return False
    name = path.name.lower()
    if (
        name in SKIP_FILES
        or name == ".env"
        or name.startswith(".env.")
        or name.endswith((".env", ".env.local"))
        or path.suffix.lower() in SKIP_SUFFIXES
    ):
        return False
    if path.stat().st_size > 50 * 1024 * 1024:
        raise RuntimeError(f"Unexpected large source asset: {relative}")
    return True


def main():
    if DEST.exists():
        raise SystemExit(f"Refusing to overwrite: {DEST}")
    paths = [ROOT / name for name in ROOT_FILES]
    for directory in DIRECTORIES:
        for folder, names, filenames in os.walk(ROOT / directory, followlinks=False):
            names[:] = [
                name for name in names
                if name not in SKIP_DIRS
                and not (Path(folder) / name).is_symlink()
                and not (Path(folder) / name).is_junction()
            ]
            for name in filenames:
                path = Path(folder) / name
                if included(path):
                    paths.append(path)
    paths = sorted(set(paths), key=lambda p: p.relative_to(ROOT).as_posix())
    for path in paths:
        if not path.is_file() or not included(path):
            raise RuntimeError(f"Invalid source: {path}")
        if path.suffix.lower() in TEXT_SUFFIXES and SECRET.search(path.read_bytes()):
            raise RuntimeError(f"Possible credential in: {path.relative_to(ROOT)}")
    readme = (
        "# 草莓项目源码分享包\n\n"
        "包含智慧草莓平台（前后端、ESP32、独立检测器、部署配置及 Windows 脚本）、"
        "图片清洗和 YOLO 视觉训练的当前源码、"
        "依赖声明、测试与项目文档。此包不是已验证的一键部署包，也不是学生版本增量更新包；"
        "不能直接覆盖现有学生项目。\n\n"
        "为避免泄露和误覆盖，未包含数据库、业务图片、数据集及标注、训练权重与 runs、"
        "saves、.runtime、.env、本机凭据、虚拟环境、node_modules、下载资源或离线运行依赖。"
        "训练前请自行取得授权数据并根据 YAML 路径准备；摄像头测试需要自行训练或导入模型。\n\n"
        "Windows 运行环境请参考各项目 README 与依赖清单自行安装。平台数据库、服务和外部"
        "模型需单独配置；实际部署、摄像头、GPU 和完整平台业务未随本包验证。"
        "不得将本包当作商业用途数据集授权或直接发布凭据。\n\n"
        "例外：老师当前 iot_service.py 在一处教学编辑中存在语法错误，分享包内该文件"
        "采用 2026-10-26 已发布且经当时验证的版本。此替换仅发生在分享包内，"
        "不修改老师源码；因此本包并非老师目录的逐字节快照。\n\n"
        "包内 manifest-sha256.json 记录每个源码文件的字节数和 SHA256；"
        "ZIP 外的 .sha256 文件用于核对整个压缩包。\n"
    )
    manifest = {}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(RELEASE) as published, zipfile.ZipFile(
            DEST, "x", zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True
        ) as archive:
            for path in paths:
                relative = path.relative_to(ROOT).as_posix()
                data = (
                    published.read(f"{RELEASE_PREFIX}/{relative}")
                    if relative == RELEASE_OVERRIDE else path.read_bytes()
                )
                if path.suffix.lower() in TEXT_SUFFIXES and SECRET.search(data):
                    raise RuntimeError(f"Possible credential in packaged copy: {relative}")
                manifest[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                archive.writestr(f"{PREFIX}/{relative}", data)
            guide = readme.encode("utf-8")
            archive.writestr(f"{PREFIX}/分享说明.md", guide)
            manifest["分享说明.md"] = {"bytes": len(guide), "sha256": hashlib.sha256(guide).hexdigest()}
            archive.writestr(
                f"{PREFIX}/manifest-sha256.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
        with zipfile.ZipFile(DEST) as archive:
            if archive.testzip():
                raise RuntimeError("ZIP CRC verification failed")
            if len(archive.namelist()) != len(manifest) + 1:
                raise RuntimeError("Unexpected archive entries")
            for relative, item in manifest.items():
                data = archive.read(f"{PREFIX}/{relative}")
                if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                    raise RuntimeError(f"Manifest mismatch: {relative}")
        with DEST.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        DEST.with_suffix(".zip.sha256").write_text(f"{digest}  {DEST.name}\n", encoding="ascii")
        print(f"READY {DEST} files={len(manifest)} bytes={DEST.stat().st_size} sha256={digest}")
    except BaseException:
        DEST.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
