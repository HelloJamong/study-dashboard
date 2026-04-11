from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.state import app_state

router = APIRouter()


class LoginRequest(BaseModel):
    user_id: str
    password: str


@router.post("/login")
async def login(req: LoginRequest):
    from src.scraper.course_scraper import CourseScraper

    if app_state.scraper:
        await app_state.scraper.close()
        app_state.scraper = None

    scraper = CourseScraper(username=req.user_id, password=req.password)
    try:
        await scraper.start()
    except RuntimeError:
        await scraper.close()
        raise HTTPException(status_code=401, detail="로그인 실패. 학번/비밀번호를 확인하세요.")
    except Exception as e:
        await scraper.close()
        raise HTTPException(status_code=500, detail=str(e))

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
