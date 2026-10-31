"""Build a full local snapshot of the three strawberry projects."""

import hashlib
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "delivery" / "Strawberry-All-Full-2026-10-31-v3.zip"
ROOTS = ("Newsmart-Strawberry", "strawberry_project", "strawberry_vision",
         "AGENTS.md", "学生版本同步", "packaging")
SKIP = (".git", ".idea", ".vscode", "__pycache__", ".pytest_cache",
        ".ruff_cache", ".venv", ".venv_new", "node_modules", "Thumbs.db")


def main():
    if ARCHIVE.exists():
        raise SystemExit(f"Refusing to overwrite: {ARCHIVE}")
    print("Archiving projects with data, models and unredacted local configuration...", flush=True)
    try:
        readme = (
            "# 草莓项目完整本机文件包（2026-10-31）\n\n"
            "包含 Newsmart-Strawberry、strawberry_project、strawberry_vision "
            "及制包/同步说明中的当前文件，包括源码、图片、标注、数据集、训练模型、"
            "运行数据和本机配置；没有脱敏。仅提供给明确授权的接收人。"
            "含登录及模型服务商凭据，泄露后须立即轮换。\n\n"
            "仅排除可重装的 .venv、.venv_new、node_modules 以及 Git/IDE/编译缓存；"
            "它们含本机路径，不属于可直接迁移的项目资料。收件人须自行安装依赖。\n\n"
            "打包时本机 PostgreSQL 127.0.0.1:15432 无法连接，因此没有导出"
            "新的逻辑数据库备份；包内仅保留 .runtime/data/postgres 文件。"
            "其他运行服务可能仍在写入，其数据未获得一致性备份保证。"
            "这不是可直接部署或可覆盖学生已有项目的更新包：不要覆盖收件人的"
            "数据库、配置、图片、模型和训练成果。\n\n"
            "软链接/目录链接不一定能迁移；新电脑须重建运行环境。"
            "本机教学编辑中的 iot_service.py 当前存在语法错误，本包原样保留，"
            "不能宣称平台可直接运行。公开病害数据来源标注为 CC BY-NC 4.0；"
            "分发前请自行核实全部第三方数据、模型和业务资料的授权范围。\n\n"
            "此包未上传或同步到其他电脑。外部 .zip.sha256 用来核对整包。\n"
        )
        with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=1, allowZip64=True) as output:
            for name in ROOTS:
                path = ROOT / name
                if path.is_file():
                    output.write(path, name)
                    continue
                for directory, subdirs, files in os.walk(path, followlinks=False):
                    subdirs[:] = [part for part in subdirs if part not in SKIP]
                    for filename in files:
                        if filename not in SKIP:
                            file = Path(directory) / filename
                            output.write(file, file.relative_to(ROOT).as_posix())
            output.writestr("完整包说明.md", readme.encode("utf-8"))
        with zipfile.ZipFile(ARCHIVE) as check:
            names = check.namelist()
            if len(names) != len(set(names)):
                raise RuntimeError("Duplicate paths in archive")
            if any(name.startswith("/") or ".." in name.split("/") for name in names):
                raise RuntimeError("Unsafe archive path")
            required = (
                "Newsmart-Strawberry/.env",
                "Newsmart-Strawberry/.runtime/local.env",
                "Newsmart-Strawberry/backend/package/yuxi/services/iot_service.py",
                "strawberry_vision/train.py",
                "strawberry_vision/data_disease.yaml",
                "strawberry_project/strawberry_classifier.py",
                "学生版本同步/AI代码同步规范.md",
                "学生版本同步/版本更新记录.md",
                "完整包说明.md",
            )
            for name in required:
                if name not in names:
                    raise RuntimeError(f"Missing required project file: {name}")
            if not any(name.startswith("strawberry_vision/dataset_disease/images/") for name in names):
                raise RuntimeError("Disease dataset images missing")
            if not any(name.startswith("Newsmart-Strawberry/.runtime/data/postgres/") for name in names):
                raise RuntimeError("Local PostgreSQL data files missing")
            if not any(name.startswith("strawberry_vision/weights/") for name in names):
                raise RuntimeError("Vision weights missing")
            print(f"Checking CRC of {len(names)} entries...", flush=True)
            bad = check.testzip()
            if bad:
                raise RuntimeError(f"ZIP CRC failure: {bad}")
        with ARCHIVE.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        ARCHIVE.with_suffix(".zip.sha256").write_text(
            f"{digest}  {ARCHIVE.name}\n", encoding="ascii"
        )
        print(f"READY {ARCHIVE} entries={len(names)} bytes={ARCHIVE.stat().st_size} sha256={digest}", flush=True)
    except BaseException:
        ARCHIVE.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
