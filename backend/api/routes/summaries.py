"""강의 요약 조회 API."""

from backend.api.state import app_state
from backend.api.summary_store import list_summaries, read_summary
from fastapi import APIRouter, HTTPException

router = APIRouter()


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


@router.get("")
async def get_summaries_list():
    _require_auth()
    return {"summaries": list_summaries()}


@router.get("/{summary_id}")
async def get_summary(summary_id: str):
    _require_auth()
    try:
        return read_summary(summary_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
