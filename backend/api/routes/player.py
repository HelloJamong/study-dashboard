import asyncio
from pathlib import Path

from backend.api.state import PlaybackProgress, app_state
from backend.api.task_manager import ManagedTask, task_manager
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class PlayRequest(BaseModel):
    course_id: str
    lecture_url: str
    lecture_title: str
    week_label: str = ""


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


def _sync_progress(state) -> None:
    app_state.playback.current = state.current
    app_state.playback.duration = state.duration
    app_state.playback.ended = state.ended
    app_state.playback.error = state.error


def _mark_lecture_completed(course_id: str, lecture_url: str) -> bool:
    """Cached course details에서 완료된 강의를 즉시 반영한다."""
    course_idx = next((i for i, course in enumerate(app_state.courses) if course.id == course_id), None)
    if course_idx is None or course_idx >= len(app_state.details):
        return False

    detail = app_state.details[course_idx]
    if not detail:
        return False

    for week in detail.weeks:
        for lecture in week.lectures:
            if lecture.full_url == lecture_url or lecture.item_url == lecture_url:
                lecture.completion = "completed"
                return True
    return False


def _write_playback_log(title: str, lecture_url: str, error: str, log_buffer: list[str]) -> str | None:
    """웹 재생 실패 로그를 파일로 남기고 경로를 반환한다."""
    try:
        from src.logger import get_error_logger

        logger, log_path = get_error_logger("web_play")
        logger.info(f"강의: {title}")
        logger.info(f"URL: {lecture_url}")
        logger.info(f"오류: {error}")
        logger.info("--- 재생 로그 ---")
        for line in log_buffer:
            logger.info(line)
        return str(Path(log_path).resolve())
    except Exception:
        return None


@router.post("/play")
async def start_play(req: PlayRequest):
    _require_auth()
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
    app_state.current_course_id = course.id
    app_state.playback = PlaybackProgress(status="playing")
    app_state.is_playing = True
    log_buffer: list[str] = []

    def on_progress(state: PlaybackState):
        _sync_progress(state)
        if not state.error:
            app_state.playback.status = "playing"

    async def run(managed: ManagedTask):
        managed.update(stage="playing", message=req.lecture_title)
        try:
            final_state = await play_lecture(
                app_state.scraper._page,
                req.lecture_url,
                on_progress=on_progress,
                debug=True,
                log_fn=log_buffer.append,
            )
            _sync_progress(final_state)

            if final_state.error == "사용자 중단":
                app_state.playback.status = "stopped"
                app_state.playback.error = None
                managed.update(status="cancelled", stage="stopped", message="재생이 중지되었습니다.")
            elif final_state.error:
                app_state.playback.status = "error"
                app_state.playback.log_path = _write_playback_log(
                    req.lecture_title,
                    req.lecture_url,
                    final_state.error,
                    log_buffer,
                )
                managed.update(status="failed", stage="error", error=final_state.error)
            elif final_state.ended:
                app_state.playback.status = "completed"
                updated = _mark_lecture_completed(req.course_id, req.lecture_url)
                if not updated:
                    app_state.playback.refresh_recommended = True
                managed.update(result={"playback_status": "completed"})
            else:
                app_state.playback.status = "stopped"
                managed.update(status="cancelled", stage="stopped", message="재생이 완료되지 않았습니다.")
        except asyncio.CancelledError:
            app_state.playback.status = "stopped"
            app_state.playback.error = None
            raise
        except Exception as e:
            app_state.playback.status = "error"
            app_state.playback.error = str(e)
            app_state.playback.log_path = _write_playback_log(
                req.lecture_title,
                req.lecture_url,
                str(e),
                log_buffer,
            )
            managed.update(status="failed", stage="error", error=str(e))
        finally:
            app_state.is_playing = False

    managed = task_manager.create(
        "player",
        run,
        metadata={
            "course_id": req.course_id,
            "lecture_title": req.lecture_title,
            "week_label": req.week_label,
        },
    )
    app_state.play_task = managed.task
    app_state.play_task_id = managed.id

    return {"started": True, "lecture": req.lecture_title, "task_id": managed.id}


@router.post("/stop")
async def stop_play():
    _require_auth()
    if app_state.play_task_id:
        await task_manager.cancel(app_state.play_task_id)
    elif app_state.play_task and not app_state.play_task.done():
        app_state.play_task.cancel()
    app_state.play_task_id = None
    app_state.is_playing = False
    app_state.playback.status = "stopped"
    app_state.playback.error = None
    return {"stopped": True}


@router.get("/status")
async def get_status():
    pb = app_state.playback
    return {
        "is_playing": app_state.is_playing,
        "course_name": app_state.current_course_name,
        "course_id": app_state.current_course_id or None,
        "lecture_title": app_state.current_lecture_title or None,
        "lecture_url": app_state.current_lecture_url or None,
        "week_label": app_state.current_week_label or None,
        "current": pb.current,
        "duration": pb.duration,
        "progress_pct": pb.progress_pct,
        "ended": pb.ended,
        "error": pb.error,
        "status": pb.status,
        "log_path": pb.log_path,
        "refresh_recommended": pb.refresh_recommended,
        "task_id": app_state.play_task_id,
    }
