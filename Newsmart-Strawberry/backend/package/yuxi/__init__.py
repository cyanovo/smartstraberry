import os
import re
import socket
import uuid
from pathlib import Path

from dotenv import load_dotenv


def _load_environment() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    repo_env = backend_dir.parent / ".env"
    runtime_env = Path.cwd() / ".env"

    if os.getenv("LOCAL_WINDOWS_MODE", "").lower() == "true":
        local_env = backend_dir.parent / ".runtime" / "local.env"
        if not local_env.is_file():
            raise RuntimeError("Run start-services.cmd before starting the local API")
        load_dotenv(local_env, override=True)
        return

    if repo_env.is_file():
        load_dotenv(repo_env, override=True)
    if runtime_env.is_file() and runtime_env.resolve() != repo_env.resolve():
        load_dotenv(runtime_env, override=True)

    if os.getenv("RUNNING_IN_DOCKER", "").lower() == "true":
        return

    classroom_env = backend_dir / "classroom.env"
    if not classroom_env.is_file():
        return
    load_dotenv(classroom_env, override=False)

    node_host = os.getenv("CLASSROOM_NODE_HOST", "").strip()
    if not node_host or node_host == "CHANGE_ME":
        raise RuntimeError("请先修改 backend/classroom.env 中的 CLASSROOM_NODE_HOST")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", node_host):
        raise RuntimeError("CLASSROOM_NODE_HOST 只能填写 IP 地址或主机名")

    machine_name = re.sub(r"[^a-z0-9-]", "-", socket.gethostname().lower()).strip("-") or "windows"
    instance_id = f"student-{machine_name}-{uuid.getnode():012x}"[-100:]
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_db = os.getenv("POSTGRES_DB", "yuxi")

    os.environ.update(
        {
            "RUNNING_IN_DOCKER": "false",
            "CLASSROOM_MODE": "true",
            "GREENHOUSE_INSTANCE_ID": instance_id,
            "POSTGRES_URL": (
                f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{node_host}:5432/{postgres_db}"
            ),
            "REDIS_URL": f"redis://{node_host}:6379/0",
            "RUN_QUEUE_NAME": f"arq:queue:{instance_id}",
            "LANGGRAPH_CHECKPOINTER_BACKEND": "postgres",
            "TRACE_DATABASE_BACKEND": "postgres",
            "TRACE_DATABASE_SCHEMA_MODE": "migrate",
            "DATABASE_SCHEMA_MODE": "migrate",
            "MINIO_URI": f"http://{node_host}:9000",
            "MINIO_PUBLIC_ENDPOINT": f"{node_host}:9000",
            "MILVUS_URI": f"http://{node_host}:19530",
            "NEO4J_URI": f"bolt://{node_host}:7687",
            "SANDBOX_PROVIDER": "provisioner",
            "SANDBOX_PROVISIONER_URL": f"http://{node_host}:8002",
            "SANDBOX_PUBLIC_HOST": node_host,
            "MQTT_ENABLED": "false",
            "MINERU_API_URI": f"http://{node_host}:30001",
            "PADDLEX_URI": f"http://{node_host}:8080",
        }
    )


_load_environment()

from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from importlib import import_module  # noqa: E402

from yuxi.config import config as config  # noqa: E402

try:
    from importlib.metadata import version

    __version__ = version("yuxi")
except Exception:
    __version__ = "unknown"

executor = ThreadPoolExecutor()  # noqa: E402


def get_version():
    """Return the Yuxi version."""
    return __version__


def __getattr__(name: str):
    if name == "knowledge_base":
        knowledge = import_module("yuxi.knowledge")
        return getattr(knowledge, name)
    raise AttributeError(f"module 'yuxi' has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | {"knowledge_base"})
