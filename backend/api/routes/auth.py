import asyncio
from contextlib import suppress

from backend.api.state import app_state
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_LOGIN_TIMEOUT_SECONDS = 45
_CLOSE_TIMEOUT_SECONDS = 10


class LoginRequest(BaseModel):
    user_id: str
    password: str


async def _close_scraper(scraper) -> None:
    """Playwright 정리를 bounded timeout 안에서 시도한다."""
    with suppress(Exception):
        await asyncio.wait_for(scraper.close(), timeout=_CLOSE_TIMEOUT_SECONDS)


@router.post("/login")
async def login(req: LoginRequest):
    from src.scraper.course_scraper import CourseScraper

    if app_state.scraper:
        await _close_scraper(app_state.scraper)
        app_state.scraper = None

    scraper = CourseScraper(username=req.user_id, password=req.password)
    try:
        await asyncio.wait_for(scraper.start(), timeout=_LOGIN_TIMEOUT_SECONDS)
    except TimeoutError:
        await _close_scraper(scraper)
        raise HTTPException(
            status_code=504,
            detail="로그인 시간이 초과되었습니다. 계정 정보를 확인하거나 잠시 후 다시 시도하세요.",
        ) from None
    except RuntimeError:
        await _close_scraper(scraper)
        raise HTTPException(status_code=401, detail="로그인 실패. 학번/비밀번호를 확인하세요.") from None
    except Exception as e:
        await _close_scraper(scraper)
        raise HTTPException(status_code=500, detail=str(e)) from e

    app_state.scraper = scraper
    app_state.user_id = req.user_id
    app_state.courses = []
    app_state.details = []

    from src.config import Config

    Config.save_credentials(req.user_id, req.password)

    return {"success": True, "user_id": req.user_id}


@router.post("/logout")
async def logout():
    if app_state.play_task and not app_state.play_task.done():
        app_state.play_task.cancel()

    if app_state.scraper:
        await app_state.scraper.close()
        app_state.scraper = None

    app_state.user_id = ""
    app_state.courses = []
    app_state.details = []
    app_state.is_playing = False

    return {"success": True}


@router.get("/status")
async def status():
    return {
        "authenticated": app_state.scraper is not None,
        "user_id": app_state.user_id,
    }
