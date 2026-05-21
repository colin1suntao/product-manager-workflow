"""Artifact API - 产物 API 路由

提供产物管理、版本管理、内容查看等 API。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from pm_workstation.artifact.artifact_manager import get_artifact_manager
from pm_workstation.artifact.artifact_models import (
    ArtifactStatus,
    ArtifactType,
)
from pm_workstation.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artifact-manager", tags=["产物管理"])


@router.get("/search", summary="搜索产物")
async def search_artifacts(
    query: str,
    limit: int = 20,
    user_id: str = Depends(get_current_user),
) -> dict:
    """搜索产物
    
    Args:
        query: 搜索关键词
        limit: 最大数量
    """
    manager = get_artifact_manager()
    artifacts = await manager.search(user_id=user_id, query=query, limit=limit)

    return {
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "name": a.name,
                "type": a.type.value,
                "preview_url": a.preview_url,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ],
        "total": len(artifacts),
        "query": query,
    }


@router.get("/session/{session_id}", summary="获取会话产物")
async def list_session_artifacts(
    session_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取会话的所有产物
    
    Args:
        session_id: 会话 ID
    """
    manager = get_artifact_manager()
    artifacts = await manager.list_by_session(session_id)

    # 过滤用户权限
    artifacts = [a for a in artifacts if a.user_id == user_id]

    return {
        "session_id": session_id,
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "name": a.name,
                "type": a.type.value,
                "current_version": a.current_version,
                "preview_url": a.preview_url,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.post("", summary="创建产物")
async def create_artifact(
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """创建新产物
    
    Args:
        body: 包含 name、type、content、description（可选）、tags（可选）等
    """
    manager = get_artifact_manager()

    name = body.get("name", "")
    type_str = body.get("type", "document")
    content = body.get("content", "")
    description = body.get("description", "")
    tags = body.get("tags", [])
    session_id = body.get("session_id")
    workflow_id = body.get("workflow_id")
    workflow_execution_id = body.get("workflow_execution_id")

    if not name:
        raise HTTPException(status_code=400, detail="产物名称不能为空")
    if not content:
        raise HTTPException(status_code=400, detail="产物内容不能为空")

    try:
        type_enum = ArtifactType(type_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的产物类型: {type_str}")

    artifact = await manager.create(
        name=name,
        type=type_enum,
        content=content,
        user_id=user_id,
        created_by=user_id,
        created_by_name="user",
        session_id=session_id,
        workflow_id=workflow_id,
        workflow_execution_id=workflow_execution_id,
        description=description,
        tags=tags,
    )

    return {
        "artifact_id": artifact.artifact_id,
        "name": artifact.name,
        "type": artifact.type.value,
        "status": artifact.status.value,
        "current_version": artifact.current_version,
        "preview_url": artifact.preview_url,
        "download_url": artifact.download_url,
        "created_at": artifact.created_at.isoformat(),
    }


@router.get("/{artifact_id}", summary="获取产物详情")
async def get_artifact(
    artifact_id: str,
    version: int | None = None,
    include_content: bool = False,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取产物详情
    
    Args:
        artifact_id: 产物 ID
        version: 版本号（可选，默认当前版本）
        include_content: 是否包含内容
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    if artifact.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此产物")

    result = {
        "artifact_id": artifact.artifact_id,
        "name": artifact.name,
        "type": artifact.type.value,
        "status": artifact.status.value,
        "description": artifact.description,
        "current_version": artifact.current_version,
        "version_count": len(artifact.versions),
        "preview_url": artifact.preview_url,
        "download_url": artifact.download_url,
        "tags": artifact.tags,
        "created_at": artifact.created_at.isoformat(),
        "updated_at": artifact.updated_at.isoformat(),
        "workflow_id": artifact.workflow_id,
        "session_id": artifact.session_id,
    }

    if include_content:
        content = await manager.get_content(artifact_id, version)
        result["content"] = content
        result["content_version"] = version or artifact.current_version

    # 版本历史摘要
    result["versions_summary"] = [
        {
            "version_number": v.version_number,
            "created_at": v.created_at.isoformat(),
            "created_by": v.created_by_name or v.created_by,
            "diff_summary": v.diff_summary,
            "size_bytes": v.size_bytes,
        }
        for v in artifact.versions
    ]

    return result


@router.patch("/{artifact_id}", summary="更新产物")
async def update_artifact(
    artifact_id: str,
    body: dict,
    user_id: str = Depends(get_current_user),
) -> dict:
    """更新产物（创建新版本）
    
    Args:
        artifact_id: 产物 ID
        body: 包含 content、diff_summary（可选）
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    if artifact.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此产物")

    if not artifact.is_editable:
        raise HTTPException(status_code=403, detail="此产物不可编辑")

    new_content = body.get("content", "")
    if not new_content:
        raise HTTPException(status_code=400, detail="内容不能为空")

    diff_summary = body.get("diff_summary")

    artifact = await manager.update(
        artifact_id=artifact_id,
        new_content=new_content,
        created_by=user_id,
        created_by_name="user",
        diff_summary=diff_summary,
    )

    return {
        "artifact_id": artifact.artifact_id,
        "name": artifact.name,
        "current_version": artifact.current_version,
        "updated_at": artifact.updated_at.isoformat(),
    }


@router.get("/{artifact_id}/versions/{version_number}", summary="获取指定版本")
async def get_artifact_version(
    artifact_id: str,
    version_number: int,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取产物的指定版本
    
    Args:
        artifact_id: 产物 ID
        version_number: 版本号
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    if artifact.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此产物")

    version = await manager.get_version(artifact_id, version_number, include_content=True)

    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {
        "artifact_id": artifact_id,
        "version_id": version.version_id,
        "version_number": version.version_number,
        "content": version.content,
        "content_type": version.content_type,
        "created_at": version.created_at.isoformat(),
        "created_by": version.created_by_name or version.created_by,
        "diff_summary": version.diff_summary,
        "diff_detail": version.diff_detail,
        "size_bytes": version.size_bytes,
    }


@router.post("/{artifact_id}/rollback/{target_version}", summary="回滚到指定版本")
async def rollback_artifact(
    artifact_id: str,
    target_version: int,
    user_id: str = Depends(get_current_user),
) -> dict:
    """回滚产物到指定版本
    
    Args:
        artifact_id: 产物 ID
        target_version: 目标版本号
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    if artifact.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此产物")

    try:
        artifact = await manager.rollback(
            artifact_id=artifact_id,
            target_version=target_version,
            created_by=user_id,
            created_by_name="user",
        )

        return {
            "artifact_id": artifact.artifact_id,
            "name": artifact.name,
            "current_version": artifact.current_version,
            "rollback_from": artifact.current_version - 1,
            "rollback_to": target_version,
            "updated_at": artifact.updated_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{artifact_id}/compare/{version_from}/{version_to}", summary="对比版本")
async def compare_versions(
    artifact_id: str,
    version_from: int,
    version_to: int,
    user_id: str = Depends(get_current_user),
) -> dict:
    """对比两个版本的差异
    
    Args:
        artifact_id: 产物 ID
        version_from: 起始版本
        version_to: 目标版本
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    if artifact.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此产物")

    diff = await manager.compare_versions(artifact_id, version_from, version_to)

    if not diff:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {
        "artifact_id": artifact_id,
        "version_from": diff.version_from,
        "version_to": diff.version_to,
        "additions": diff.additions,
        "deletions": diff.deletions,
        "similarity": diff.similarity,
        "diff_content": diff.diff_content,
    }


@router.delete("/{artifact_id}", summary="删除产物")
async def delete_artifact(
    artifact_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """删除产物（标记为已删除）
    
    Args:
        artifact_id: 产物 ID
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    if artifact.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权删除此产物")

    success = await manager.delete(artifact_id)

    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return {"message": "产物已删除", "artifact_id": artifact_id}


@router.get("", summary="获取产物列表")
async def list_artifacts(
    type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user),
) -> dict:
    """获取用户的产物列表
    
    Args:
        type: 类型过滤（可选）
        status: 状态过滤（可选）
        limit: 最大数量
    """
    manager = get_artifact_manager()

    type_filter = None
    if type:
        try:
            type_filter = ArtifactType(type)
        except ValueError:
            pass

    status_filter = None
    if status:
        try:
            status_filter = ArtifactStatus(status)
        except ValueError:
            pass

    artifacts = await manager.list_by_user(
        user_id=user_id,
        type_filter=type_filter,
        status_filter=status_filter,
        limit=limit,
    )

    return {
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "name": a.name,
                "type": a.type.value,
                "status": a.status.value,
                "current_version": a.current_version,
                "version_count": len(a.versions),
                "preview_url": a.preview_url,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
                "workflow_id": a.workflow_id,
                "session_id": a.session_id,
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.get("/{artifact_id}/preview", summary="预览产物")
async def preview_artifact(
    artifact_id: str,
    version: int | None = None,
    request: Request = None,
) -> HTMLResponse:
    """预览产物内容
    
    Args:
        artifact_id: 产物 ID
        version: 版本号（可选）
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTMLResponse(content="<h1>产物不存在</h1>", status_code=404)

    content = await manager.get_content(artifact_id, version or artifact.current_version)

    if not content:
        return HTMLResponse(content="<h1>内容不存在</h1>", status_code=404)

    # 根据类型渲染
    if artifact.type == ArtifactType.PROTOTYPE:
        # HTML 原型直接返回
        return HTMLResponse(content=content)
    elif artifact.type in [ArtifactType.DOCUMENT, ArtifactType.REPORT]:
        # Markdown 文档需要转换为 HTML（简化实现）
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{artifact.name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        pre {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        code {{
            background: #f5f5f5;
            padding: 2px 4px;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>{artifact.name}</h1>
    <div id="content">
        <!-- 简化实现：直接显示原始内容 -->
        <pre>{content}</pre>
    </div>
</body>
</html>
"""
        return HTMLResponse(content=html)
    else:
        return HTMLResponse(content=f"<pre>{content}</pre>")


@router.get("/{artifact_id}/download", summary="下载产物")
async def download_artifact(
    artifact_id: str,
    version: int | None = None,
) -> FileResponse:
    """下载产物文件
    
    Args:
        artifact_id: 产物 ID
        version: 版本号（可选）
    """
    manager = get_artifact_manager()
    artifact = await manager.get(artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="产物不存在")

    target_version = version or artifact.current_version
    content_path = manager._get_content_path(artifact_id, target_version)

    if not artifact.file_path or not artifact.file_path.endswith(".txt"):
        # 动态生成文件路径
        manager._save_content(artifact_id, target_version, await manager.get_content(artifact_id, target_version))

    # 确定文件扩展名
    extension_map = {
        ArtifactType.PROTOTYPE: ".html",
        ArtifactType.DOCUMENT: ".md",
        ArtifactType.REPORT: ".md",
        ArtifactType.IMAGE: ".png",
        ArtifactType.DATA: ".json",
        ArtifactType.CODE: ".txt",
    }
    extension = extension_map.get(artifact.type, ".txt")

    filename = f"{artifact.name}-v{target_version}{extension}"

    return FileResponse(
        path=content_path,
        filename=filename,
        media_type="application/octet-stream",
    )
