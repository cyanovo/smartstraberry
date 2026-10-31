from __future__ import annotations

from dataclasses import dataclass
import os

from deepagents.backends import FilesystemBackend, StateBackend

from deepagents.backends.composite import (
    CompositeBackend,
    _remap_file_info_path,
    _route_for_path,
    _strip_route_from_pattern,
)
from deepagents.backends.protocol import EditResult, FileInfo, FileUploadResponse, GlobResult, WriteResult
from deepagents.middleware.filesystem import FilesystemMiddleware

from yuxi.agents.skills.service import normalize_string_list
from yuxi.utils.paths import VIRTUAL_PATH_CONVERSATION_HISTORY, VIRTUAL_PATH_LARGE_TOOL_RESULTS, VIRTUAL_PATH_OUTPUTS

from .sandbox import ProvisionerSandboxBackend
from .skills_backend import SelectedSkillsReadonlyBackend


def _coerce_glob_result(result) -> GlobResult:
    if isinstance(result, GlobResult):
        return result
    return GlobResult(matches=result or [])


class _ReadonlyUploadsBackend(FilesystemBackend):
    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error="Uploaded files are read-only.")

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        return EditResult(error="Uploaded files are read-only.")

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return [FileUploadResponse(path=path, error="permission_denied") for path, _ in files]


class CustomCompositeBackend(CompositeBackend):
    """修复 glob 路由逻辑的 CompositeBackend。"""

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        backend, backend_path, route_prefix = _route_for_path(
            default=self.default,
            sorted_routes=self.sorted_routes,
            path=path,
        )
        if route_prefix is not None:
            result = _coerce_glob_result(backend.glob(pattern, backend_path))
            if result.error:
                return result
            return GlobResult(matches=[_remap_file_info_path(fi, route_prefix) for fi in (result.matches or [])])

        if path is None or path == "/":
            results: list[FileInfo] = []
            default_result = _coerce_glob_result(self.default.glob(pattern, path))
            if default_result.error:
                return default_result
            results.extend(default_result.matches or [])
            for route_prefix, backend in self.routes.items():
                route_pattern = _strip_route_from_pattern(pattern, route_prefix)
                result = _coerce_glob_result(backend.glob(route_pattern, "/"))
                if result.error:
                    return result
                results.extend(_remap_file_info_path(fi, route_prefix) for fi in (result.matches or []))
            results.sort(key=lambda x: x.get("path", ""))
            return GlobResult(matches=results)

        return _coerce_glob_result(self.default.glob(pattern, path))

    async def aglob(self, pattern: str, path: str = "/") -> GlobResult:
        backend, backend_path, route_prefix = _route_for_path(
            default=self.default,
            sorted_routes=self.sorted_routes,
            path=path,
        )
        if route_prefix is not None:
            result = _coerce_glob_result(await backend.aglob(pattern, backend_path))
            if result.error:
                return result
            return GlobResult(matches=[_remap_file_info_path(fi, route_prefix) for fi in (result.matches or [])])

        if path is None or path == "/":
            results: list[FileInfo] = []
            default_result = _coerce_glob_result(await self.default.aglob(pattern, path))
            if default_result.error:
                return default_result
            results.extend(default_result.matches or [])
            for route_prefix, backend in self.routes.items():
                route_pattern = _strip_route_from_pattern(pattern, route_prefix)
                result = _coerce_glob_result(await backend.aglob(route_pattern, "/"))
                if result.error:
                    return result
                results.extend(_remap_file_info_path(fi, route_prefix) for fi in (result.matches or []))
            results.sort(key=lambda x: x.get("path", ""))
            return GlobResult(matches=results)

        return _coerce_glob_result(await self.default.aglob(pattern, path))


@dataclass(frozen=True)
class _BackendScope:
    thread_id: str
    uid: str
    readable_skills: list[str]
    file_thread_id: str
    skills_thread_id: str

    @classmethod
    def from_runtime(cls, runtime) -> _BackendScope:
        config = getattr(runtime, "config", None)
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
        context = getattr(runtime, "context", None)
        state = getattr(runtime, "state", None)
        return cls.from_sources(
            configurable if isinstance(configurable, dict) else {},
            context,
            state if isinstance(state, dict) else {},
            readable_skills_source=context,
            error_context="runtime configurable context",
        )

    @classmethod
    def from_sources(cls, *sources, readable_skills_source, error_context: str) -> _BackendScope:
        def string_value(key: str) -> str | None:
            for source in sources:
                value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return None

        thread_id = string_value("thread_id")
        if not thread_id:
            raise ValueError(f"thread_id is required in {error_context}")

        uid = string_value("uid")
        if not uid:
            raise ValueError(f"uid is required in {error_context}")

        selected = getattr(readable_skills_source, "_readable_skills", [])
        return cls(
            thread_id=thread_id,
            uid=uid,
            readable_skills=normalize_string_list(selected if isinstance(selected, list) else []),
            file_thread_id=string_value("file_thread_id") or thread_id,
            skills_thread_id=string_value("skills_thread_id") or thread_id,
        )

    def create_backend(self) -> CompositeBackend:
        if os.getenv("LOCAL_WINDOWS_MODE") == "true":
            from yuxi.agents.backends.sandbox.paths import (
                ensure_thread_dirs,
                sandbox_outputs_dir,
                sandbox_uploads_dir,
                sandbox_workspace_dir,
            )
            from yuxi.utils.paths import VIRTUAL_PATH_UPLOADS, VIRTUAL_PATH_WORKSPACE, VIRTUAL_SKILLS_PATH

            ensure_thread_dirs(self.file_thread_id, self.uid)
            skills = SelectedSkillsReadonlyBackend(selected_slugs=self.readable_skills)
            return CustomCompositeBackend(
                default=StateBackend(),
                routes={
                    VIRTUAL_PATH_WORKSPACE + "/": FilesystemBackend(
                        root_dir=sandbox_workspace_dir(self.file_thread_id, self.uid), virtual_mode=True
                    ),
                    VIRTUAL_PATH_UPLOADS + "/": _ReadonlyUploadsBackend(
                        root_dir=sandbox_uploads_dir(self.file_thread_id), virtual_mode=True
                    ),
                    VIRTUAL_PATH_OUTPUTS + "/": FilesystemBackend(
                        root_dir=sandbox_outputs_dir(self.file_thread_id), virtual_mode=True
                    ),
                    "/skills/": skills,
                    VIRTUAL_SKILLS_PATH + "/": skills,
                },
                artifacts_root=VIRTUAL_PATH_OUTPUTS,
            )
        return CustomCompositeBackend(
            default=ProvisionerSandboxBackend(
                thread_id=self.thread_id,
                uid=self.uid,
                readable_skills=self.readable_skills,
                file_thread_id=self.file_thread_id,
                skills_thread_id=self.skills_thread_id,
            ),
            routes={
                "/skills/": SelectedSkillsReadonlyBackend(selected_slugs=self.readable_skills),
            },
            artifacts_root=VIRTUAL_PATH_OUTPUTS,
        )


def create_agent_composite_backend(runtime) -> CompositeBackend:
    return _BackendScope.from_runtime(runtime).create_backend()


def create_agent_filesystem_middleware(
    tool_token_limit_before_evict: int | None = None,
    *,
    context=None,
) -> FilesystemMiddleware:
    backend = create_agent_composite_backend
    if context is not None:
        backend = _BackendScope.from_sources(
            context,
            readable_skills_source=context,
            error_context="runtime context",
        ).create_backend()
    middleware = FilesystemMiddleware(
        backend=backend,
        tool_token_limit_before_evict=tool_token_limit_before_evict,
    )
    middleware._large_tool_results_prefix = VIRTUAL_PATH_LARGE_TOOL_RESULTS
    middleware._conversation_history_prefix = VIRTUAL_PATH_CONVERSATION_HISTORY
    return middleware
