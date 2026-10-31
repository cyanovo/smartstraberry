import os

from fastapi import APIRouter

from server.routers.auth_router import auth
from server.routers.agent_router import agent_router
from server.routers.chat_router import chat
from server.routers.dashboard_router import dashboard
from server.routers.auth_dept_router import department
from server.routers.mcp_router import mcp
from server.routers.model_provider_router import model_providers
from server.routers.skill_router import skills, user_skills
from server.routers.system_router import system
from server.routers.system_task_router import tasks
from server.routers.tool_router import tools
from server.routers.user_router import user_router
from server.routers.filesystem_router import filesystem_router
from server.routers.workspace_router import workspace
from server.routers.mention_router import mention_router
from server.routers.iot_router import iot
from server.routers.detect_router import detect
from server.routers.trace_router import trace
from server.routers.vlm_router import vlm
from server.routers.album_router import albums
from server.routers.field_work_router import field_work
from server.routers.disease_care_router import disease_care

_LITE_MODE = os.environ.get("LITE_MODE", "").lower() in ("true", "1")

router = APIRouter()

# 基础系统接口：健康检查、配置、认证与聊天主链路。
router.include_router(system)  # /api/system/* 系统状态与全局配置
router.include_router(auth)  # /api/auth/* 登录与用户信息
router.include_router(agent_router)  # /api/agent/* 智能体管理与运行态
router.include_router(chat)  # /api/chat/* 对话线程、消息历史与附件

# 管理与工作台接口：后台任务、权限域以及工具体系配置。
router.include_router(dashboard)  # /api/dashboard/* 仪表盘聚合数据
router.include_router(department)  # /api/departments/* 部门与权限相关数据
router.include_router(tasks)  # /api/tasks/* 后台任务查询与管理
router.include_router(mcp)  # /api/system/mcp-servers/* MCP 服务管理
router.include_router(model_providers)  # /api/system/model-providers/* 独立模型配置
router.include_router(skills)  # /api/system/skills/* Skills 管理
router.include_router(user_skills)  # /api/skills/* 用户可用 Skills
router.include_router(tools)  # /api/system/tools/* 工具列表与配置
router.include_router(user_router)  # /api/user/* 用户级配置与凭据
router.include_router(filesystem_router)  # /api/viewer/filesystem/* 工作台文件系统视图
router.include_router(workspace)  # /api/workspace/* 用户个人工作区
router.include_router(mention_router)  # /api/mention/* 提及文件搜索接口
router.include_router(iot)  # /api/iot/* 智能温室物联网
router.include_router(detect)  # /api/detect/* 番茄成熟度检测
router.include_router(trace)  # /api/trace/* 番茄溯源
router.include_router(vlm)  # /api/vlm/* 大模型视觉识别
router.include_router(albums)
router.include_router(field_work)
router.include_router(disease_care)

if not _LITE_MODE or os.getenv("LOCAL_WINDOWS_MODE") == "true":
    from server.routers.graph_router import graph
    from server.routers.knowledge_router import knowledge
    from server.routers.knowledge_eval_router import evaluation

    # 本地模式保留管理接口；可创建的类型仍由知识库工厂按依赖配置决定。
    router.include_router(knowledge)  # /api/knowledge/* 知识库管理与检索
    router.include_router(evaluation)  # /api/evaluation/* 知识库评估
    router.include_router(graph)  # /api/graph/* 图谱查询与管理
