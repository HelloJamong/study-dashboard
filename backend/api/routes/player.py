import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.state import PlaybackProgress, app_state

router = APIRouter()


class PlayRequest(BaseModel):
    course_id: str
    lecture_url: str
    lecture_title: str
    week_label: str = ""


@router.post("/play")
async def start_play(req: PlayRequest):
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if app_state.is_playing:
        raise HTTPException(status_code=409, detail="이미 재생 중입니다.")

    course = next((c for c in app_state.courses if c.id == req.course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="과목을 찾을 수 없습니다.")

    from src.player.background_player import PlaybackState, play_lecture

    app_state.current_lecture_title = req.lecture_title
    app_state.current_lecture_url = req.lecture_url
    app_state.current_week_label = req.week_label
    app_state.current_course_name = course.long_name
    app_state.playback = PlaybackProgress()
    app_state.is_playing = True

    def on_progress(state: PlaybackState):
        app_state.playback.current = state.current
        app_state.playback.duration = state.duration
        app_state.playback.ended = state.ended
        app_state.playback.error = state.error

    async def run():
        try:
            await play_lecture(
                app_state.scraper._page,
                req.lecture_url,
                on_progress=on_progress,
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            app_state.playback.error = str(e)
        finally:
            app_state.is_playing = False

    task = asyncio.create_task(run())
    app_state.play_task = task

    return {"started": True, "lecture": req.lecture_title}


@router.post("/stop")
async def stop_play():
    if app_state.play_task and not app_state.play_task.done():
        app_state.play_task.cancel()
    app_state.is_playing = False
    return {"stopped": True}


@router.get("/status")
async def get_status():
    pb = app_state.playback
    return {
        "is_playing": app_state.is_playing,
        "course_name": app_state.current_course_name,
        "lecture_title": app_state.current_lecture_title or None,
        "week_label": app_state.current_week_label or None,
        "current": pb.current,
        "duration": pb.duration,
        "progress_pct": pb.progress_pct,
        "ended": pb.ended,
        "error": pb.error,
    }
