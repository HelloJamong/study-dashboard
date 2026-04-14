"""공통 백그라운드 태스크 상태 API."""

from backend.api.state import app_state
from backend.api.task_manager import task_manager
from fastapi import APIRouter, HTTPException

router = APIRouter()


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


@router.get("")
async def list_tasks():
    _require_auth()
    return {"tasks": [task.to_dict() for task in task_manager.list()]}


@router.get("/{task_id}")
async def get_task(task_id: str):
    _require_auth()
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return task.to_dict()


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    _require_auth()
    cancelled = await task_manager.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    task = task_manager.get(task_id)
    return task.to_dict() if task else {"cancelled": True}
