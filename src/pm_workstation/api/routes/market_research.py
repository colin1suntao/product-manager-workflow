"""市场调研 API 路由

提供市场调研报告的创建、查询和管理接口。
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from pm_workstation.agents.market_research_agent import MarketResearchAgent
from pm_workstation.auth.dependencies import get_current_user, get_current_user_optional
from pm_workstation.skills.loader import SkillLoader

router = APIRouter(prefix="/market-research", tags=["市场调研"])

# 内存存储（生产环境应使用数据库）
_research_tasks: dict[str, dict] = {}
_research_reports: dict[str, dict] = {}
_research_templates: dict[str, dict] = {}

# 全局技能加载器实例
_skill_loader: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    """获取技能加载器实例"""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader


def _get_llm_handler(request: Request):
    """从 app.state 获取 LLM handler"""
    return getattr(request.app.state, 'llm_handler', None)


@router.post("/create", summary="创建调研任务")
async def create_research(
    request: Request,
    body: dict,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
) -> dict:
    """创建市场调研任务

    Args:
        body: 包含 title, requirement_text, selected_skills 的请求体
    """
    title = body.get("title", "")
    requirement_text = body.get("requirement_text", "")
    selected_skills = body.get("selected_skills", [])
    template_id = body.get("template_id")

    if not requirement_text:
        raise HTTPException(status_code=400, detail="调研需求描述不能为空")

    # 如果指定了模板，使用模板的技能列表
    if template_id and template_id in _research_templates:
        template = _research_templates[template_id]
        selected_skills = template.get("skill_names", selected_skills)

    if not selected_skills:
        raise HTTPException(status_code=400, detail="请选择至少一个 PM Skills")

    # 创建任务
    task_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())

    _research_tasks[task_id] = {
        "id": task_id,
        "report_id": report_id,
        "user_id": user_id,
        "title": title or f"市场调研 - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "requirement_text": requirement_text,
        "selected_skills": selected_skills,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error_message": None,
    }

    # 创建报告占位
    _research_reports[report_id] = {
        "id": report_id,
        "task_id": task_id,
        "user_id": user_id,
        "title": _research_tasks[task_id]["title"],
        "requirement_text": requirement_text,
        "selected_skills": selected_skills,
        "report_content": "",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    # 后台执行生成任务
    background_tasks.add_task(
        _generate_research_report,
        task_id=task_id,
        report_id=report_id,
        requirement_text=requirement_text,
        selected_skills=selected_skills,
        request=request,
    )

    return {
        "task_id": task_id,
        "report_id": report_id,
        "status": "pending",
        "message": "调研任务已创建，正在后台生成",
    }


async def _generate_research_report(
    task_id: str,
    report_id: str,
    requirement_text: str,
    selected_skills: list[str],
    request: Request,
) -> None:
    """后台生成调研报告"""
    try:
        # 更新任务状态
        _research_tasks[task_id]["status"] = "running"
        _research_tasks[task_id]["started_at"] = datetime.now().isoformat()
        _research_reports[report_id]["status"] = "running"

        # 动态获取最新的 LLM handler（而不是依赖 app.state）
        provider_store = request.app.state.provider_store
        default_config = await provider_store.get_default_config()
        
        if not default_config:
            raise Exception("LLM 未配置，请先在设置页面配置 LLM Provider")
        
        from pm_workstation.api.app import _build_llm_handler
        llm_handler = _build_llm_handler(default_config)
        
        if not llm_handler:
            raise Exception("LLM 配置无效，请检查 API Key 和模型配置")

        # 创建 agent
        agent = MarketResearchAgent(llm_handler=llm_handler)

        # 生成报告
        report_content = await agent.generate_report(
            requirement_text=requirement_text,
            selected_skills=selected_skills,
        )

        # 更新报告
        _research_reports[report_id]["report_content"] = report_content
        _research_reports[report_id]["status"] = "completed"
        _research_reports[report_id]["completed_at"] = datetime.now().isoformat()

        # 更新任务状态
        _research_tasks[task_id]["status"] = "completed"
        _research_tasks[task_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        # 更新失败状态
        _research_tasks[task_id]["status"] = "failed"
        _research_tasks[task_id]["error_message"] = str(e)
        _research_reports[report_id]["status"] = "failed"


@router.get("/list", summary="获取调研报告列表")
async def list_researches(
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取用户的调研报告列表"""
    reports = [
        {
            "id": report["id"],
            "title": report["title"],
            "status": report["status"],
            "selected_skills": report["selected_skills"],
            "created_at": report["created_at"],
            "completed_at": report["completed_at"],
        }
        for report in _research_reports.values()
        if report["user_id"] == user_id
    ]

    # 按创建时间倒序排列
    reports.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "reports": reports,
        "total": len(reports),
    }


@router.get("/{report_id}", summary="获取调研报告详情")
async def get_research(
    report_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取调研报告详情"""
    report = _research_reports.get(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="调研报告不存在")

    if report["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问此报告")

    return report


@router.get("/{report_id}/status", summary="获取任务执行状态")
async def get_research_status(
    report_id: str,
) -> dict:
    """获取调研任务的执行状态"""
    report = _research_reports.get(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="调研报告不存在")

    task_id = report.get("task_id")
    task = _research_tasks.get(task_id, {})

    return {
        "report_id": report_id,
        "task_id": task_id,
        "status": report["status"],
        "started_at": task.get("started_at"),
        "completed_at": report.get("completed_at"),
        "error_message": task.get("error_message"),
    }


@router.post("/recommend-skills", summary="推荐调研技能")
async def recommend_skills(
    request: Request,
    body: dict,
    user_id: str | None = Depends(get_current_user_optional),
) -> dict:
    """根据调研需求推荐相关的 PM Skills

    Args:
        body: 包含 requirement_text 的请求体
    """
    requirement_text = body.get("requirement_text", "")

    if not requirement_text:
        raise HTTPException(status_code=400, detail="调研需求描述不能为空")

    agent = MarketResearchAgent(llm_handler=None)

    recommendations = agent.recommend_skills(requirement_text)

    return {
        "recommendations": [r.to_dict() for r in recommendations],
        "total": len(recommendations),
    }


@router.post("/templates", summary="保存调研模板")
async def save_template(
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """保存调研技能组合为模板

    Args:
        body: 包含 name, description, skill_names 的请求体
    """
    name = body.get("name", "")
    description = body.get("description", "")
    skill_names = body.get("skill_names", [])

    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    if not skill_names:
        raise HTTPException(status_code=400, detail="请选择至少一个技能")

    template_id = str(uuid.uuid4())

    _research_templates[template_id] = {
        "id": template_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "skill_names": skill_names,
        "created_at": datetime.now().isoformat(),
    }

    return {
        "id": template_id,
        "name": name,
        "description": description,
        "skill_names": skill_names,
        "message": "模板保存成功",
    }


@router.get("/templates/list", summary="获取模板列表")
async def list_templates(
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取用户的调研模板列表"""
    templates = [
        template
        for template in _research_templates.values()
        if template["user_id"] == user_id
    ]

    # 按创建时间倒序排列
    templates.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "templates": templates,
        "total": len(templates),
    }


@router.delete("/templates/{template_id}", summary="删除调研模板")
async def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """删除指定的调研模板"""
    template = _research_templates.get(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if template["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权删除此模板")

    del _research_templates[template_id]

    return {"message": "模板删除成功"}
