"""PM Skills API 路由

提供 Product-Manager-Skills 的管理和查询接口。
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.skills.loader import SkillLoader

router = APIRouter(prefix="/skills", tags=["PM Skills"])

# 全局技能加载器实例
_skill_loader: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    """获取技能加载器实例"""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader


@router.get("/list", summary="列出所有可用技能")
async def list_skills(
    user_id: str = Depends(get_current_user),
    skill_type: str | None = None,
) -> dict:
    """列出所有可用的 PM Skills

    Args:
        skill_type: 技能类型过滤（component/interactive/workflow）
    """
    loader = get_skill_loader()

    if skill_type:
        # 按类型过滤
        skills = [
            {
                "name": skill.name,
                "description": skill.description,
                "type": skill.skill_type,
                "best_for": skill.best_for,
                "scenarios": skill.scenarios[:2] if skill.scenarios else [],
                "estimated_time": skill.estimated_time,
            }
            for skill in loader._skills.values()
            if skill.skill_type == skill_type
        ]
    else:
        # 返回所有技能
        skills = [
            {
                "name": skill.name,
                "description": skill.description,
                "type": skill.skill_type or "native",
                "best_for": skill.best_for,
                "scenarios": skill.scenarios[:2] if skill.scenarios else [],
                "estimated_time": skill.estimated_time,
            }
            for skill in loader._skills.values()
        ]

    return {
        "skills": skills,
        "total": len(skills),
    }


@router.get("/types", summary="获取技能类型统计")
async def get_skill_types(
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取技能类型统计信息"""
    loader = get_skill_loader()

    type_counts = {}
    for skill in loader._skills.values():
        skill_type = skill.skill_type or "native"
        type_counts[skill_type] = type_counts.get(skill_type, 0) + 1

    return {
        "types": type_counts,
        "total": len(loader._skills),
    }


@router.get("/{skill_name}", summary="获取技能详情")
async def get_skill_detail(
    skill_name: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取指定技能的详细信息"""
    loader = get_skill_loader()
    skill = loader.load(skill_name)

    if not skill:
        raise HTTPException(status_code=404, detail=f"技能 '{skill_name}' 不存在")

    return {
        "name": skill.name,
        "description": skill.description,
        "intent": skill.intent,
        "type": skill.skill_type or "native",
        "best_for": skill.best_for,
        "scenarios": skill.scenarios,
        "estimated_time": skill.estimated_time,
        "system_prompt": skill.system_prompt,
        "steps": skill.steps,
    }


@router.post("/{skill_name}/apply", summary="应用技能到需求")
async def apply_skill(
    skill_name: str,
    request: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """应用指定技能来处理需求

    Args:
        skill_name: 技能名称
        request: 包含 requirement_text 的请求体
    """
    loader = get_skill_loader()
    skill = loader.load(skill_name)

    if not skill:
        raise HTTPException(status_code=404, detail=f"技能 '{skill_name}' 不存在")

    requirement_text = request.get("requirement_text", "")
    if not requirement_text:
        raise HTTPException(status_code=400, detail="需求文本不能为空")

    # 返回技能的应用提示
    return {
        "skill_name": skill.name,
        "system_prompt": skill.system_prompt,
        "full_prompt": skill.get_full_prompt(),
        "requirement_text": requirement_text,
    }


@router.post("/import", summary="导入技能")
async def import_skill(
    request: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """导入用户自定义技能

    支持两种格式：
    1. content: SKILL.md 格式内容（含 YAML front matter）
    2. 直接传入技能字段（name, description, system_prompt 等）
    """
    loader = get_skill_loader()

    content = request.get("content", "").strip()

    try:
        if content:
            skill = loader.import_skill(content)
        else:
            skill = loader.import_skill_from_dict(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "name": skill.name,
        "description": skill.description,
        "type": skill.skill_type or "component",
        "message": f"技能 '{skill.name}' 导入成功",
    }


@router.post("/import/file", summary="通过文件上传导入技能")
async def import_skill_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
) -> dict:
    """通过上传 SKILL.md 文件导入技能"""
    loader = get_skill_loader()

    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="仅支持 .md 文件")

    try:
        content = (await file.read()).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8 编码")

    try:
        skill = loader.import_skill(content, filename=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "name": skill.name,
        "description": skill.description,
        "type": skill.skill_type or "component",
        "message": f"技能 '{skill.name}' 导入成功",
    }


@router.delete("/{skill_name}", summary="删除已导入的技能")
async def delete_skill(
    skill_name: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """删除用户导入的技能（内置技能不可删除）"""
    loader = get_skill_loader()

    if not loader.is_imported(skill_name):
        raise HTTPException(status_code=400, detail=f"技能 '{skill_name}' 不是导入的技能，无法删除")

    success = loader.delete_skill(skill_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"技能 '{skill_name}' 不存在")

    return {"message": f"技能 '{skill_name}' 已删除"}
