"""행위 로그 조회 API."""

from backend.api.state import app_state
from fastapi import APIRouter, HTTPException, Query

from src.event_log import list_events

router = APIRouter()


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


@router.get("")
async def get_logs(
    event_type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    _require_auth()
    return {"events": list_events(event_type=event_type, status=status, limit=limit)}
