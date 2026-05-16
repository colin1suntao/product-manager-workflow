"""Token 用量统计 API"""

from fastapi import APIRouter, Depends

from pm_workstation.auth.dependencies import get_current_user
from pm_workstation.llm.token_usage import TokenUsageStore

router = APIRouter(prefix="/token-usage", tags=["模型用量"])


def _get_store() -> TokenUsageStore:
    return TokenUsageStore()


@router.get("/overview", summary="用量总览")
async def get_overview(
    days: int = 30,
    user_id: str = Depends(get_current_user),
    store: TokenUsageStore = Depends(_get_store),
) -> dict:
    overview = store.get_overview(days=days)
    return overview.model_dump()


@router.get("/records", summary="用量明细")
async def get_records(
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(get_current_user),
    store: TokenUsageStore = Depends(_get_store),
) -> dict:
    records = store.get_records(limit=limit, offset=offset)
    return {
        "records": [r.model_dump() for r in records],
        "total": len(store._records),
    }
