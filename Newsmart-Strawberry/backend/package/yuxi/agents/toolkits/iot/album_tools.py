from langgraph.prebuilt.tool_node import ToolRuntime

from yuxi.agents.toolkits.registry import tool


@tool(category="buildin", tags=["草莓", "照片集"], display_name="分析草莓照片集")
async def analyze_strawberry_album(
    album_id: str, runtime: ToolRuntime, kb_id: str = "", average_mass_g: float | None = None,
    disease_record_ids: list[str] | None = None,
) -> dict:
    """按照片集读取证据，可用 disease_record_ids 指定病虫害记录。跨集记录仅作参考，不推断整棚产量。"""
    from yuxi.repositories.user_repository import UserRepository
    from yuxi.services.field_analysis_service import analyze_album

    user = await UserRepository().get_by_uid(str(runtime.context.uid))
    if not user or not user.department_id:
        return {"error": "用户无效"}
    if average_mass_g is not None and not 0 < average_mass_g <= 500:
        return {"error": "平均单果质量必须来自用户实测，范围 0-500 克"}
    return await analyze_album(album_id, kb_id or None, average_mass_g, user, disease_record_ids)
