"""자동 모드 API — 미시청 강의를 스케줄에 따라 자동 재생한다."""

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta

from backend.api.state import PlaybackProgress, app_state
from backend.api.task_manager import ManagedTask, task_manager
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_DEFAULT_SCHEDULE_HOURS = [9, 13, 18, 23]

try:
    from src.config import KST
except Exception:
    from zoneinfo import ZoneInfo

    KST = ZoneInfo("Asia/Seoul")


class AutoStartRequest(BaseModel):
    schedule_hours: list[int] = _DEFAULT_SCHEDULE_HOURS


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


def _next_schedule_time(schedule_hours: list[int]) -> datetime:
    now = datetime.now(KST)
    today = [now.replace(hour=h, minute=0, second=0, microsecond=0) for h in sorted(schedule_hours)]
    for t in today:
        if t > now:
            return t
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=sorted(schedule_hours)[0], minute=0, second=0, microsecond=0)


async def _run_auto_cycle(schedule_hours: list[int]) -> None:
    """미시청 강의를 한 사이클 순차 재생한다."""
    from backend.api.routes.player import _mark_lecture_completed, _write_playback_log

    from src.player.background_player import play_lecture

    if not app_state.scraper:
        app_state.auto.error = "로그인 상태가 아닙니다."
        app_state.auto.enabled = False
        return

    app_state.auto.error = None

    # 강의 목록 갱신
    try:
        courses = await app_state.scraper.fetch_courses()
        details = await app_state.scraper.fetch_all_details(courses)
        app_state.courses = courses
        app_state.details = details
    except asyncio.CancelledError:
        raise
    except Exception as e:
        app_state.auto.error = f"강의 목록 갱신 실패: {e}"
        return

    # 미시청 강의 수집
    pending: list[tuple] = []
    for course, detail in zip(courses, details, strict=False):
        if detail is None:
            continue
        for lec in detail.all_video_lectures:
            if lec.needs_watch:
                pending.append((course, lec))

    if not pending:
        app_state.auto.current_lecture = ""
        app_state.auto.current_course = ""
        next_time = _next_schedule_time(schedule_hours)
        app_state.auto.next_run_at = next_time.strftime("%H:%M")
        return

    for course, lec in pending:
        if not app_state.auto.enabled:
            break

        # 수동 재생 중이면 완료 대기
        while app_state.is_playing and app_state.auto.enabled:
            await asyncio.sleep(2)

        if not app_state.auto.enabled:
            break

        app_state.auto.current_course = course.long_name
        app_state.auto.current_lecture = lec.title

        log_buffer: list[str] = []
        app_state.current_lecture_title = lec.title
        app_state.current_lecture_url = lec.full_url
        app_state.current_week_label = lec.week_label
        app_state.current_course_name = course.long_name
        app_state.playback = PlaybackProgress(status="playing")
        app_state.is_playing = True

        def _on_progress(s):
            app_state.playback.current = s.current
            app_state.playback.duration = s.duration
            app_state.playback.ended = s.ended
            app_state.playback.error = s.error

        try:
            final_state = await play_lecture(
                app_state.scraper._page,
                lec.full_url,
                on_progress=_on_progress,
                debug=True,
                log_fn=log_buffer.append,
            )
            _on_progress(final_state)

            if final_state.error == "사용자 중단":
                app_state.playback.status = "stopped"
                app_state.auto.enabled = False
                break
            elif final_state.error:
                app_state.playback.status = "error"
                app_state.playback.log_path = _write_playback_log(
                    lec.title, lec.full_url, final_state.error, log_buffer
                )
            elif final_state.ended:
                app_state.playback.status = "completed"
                updated = _mark_lecture_completed(course.id, lec.full_url)
                if not updated:
                    app_state.playback.refresh_recommended = True
                app_state.auto.processed_count += 1
            else:
                app_state.playback.status = "stopped"

        except asyncio.CancelledError:
            app_state.playback.status = "stopped"
            app_state.is_playing = False
            raise
        except Exception as e:
            app_state.playback.status = "error"
            app_state.playback.error = str(e)
            app_state.playback.log_path = _write_playback_log(
                lec.title, lec.full_url, str(e), log_buffer
            )
        finally:
            app_state.is_playing = False
            with suppress(Exception):
                await app_state.scraper._page.goto(
                    "about:blank", wait_until="domcontentloaded", timeout=5000
                )

        await asyncio.sleep(1)

    app_state.auto.current_course = ""
    app_state.auto.current_lecture = ""


async def _auto_loop(schedule_hours: list[int]) -> None:
    """자동 모드 백그라운드 루프 — 즉시 1회 실행 후 스케줄 대기."""
    first_run = True
    try:
        while app_state.auto.enabled:
            if not first_run:
                next_time = _next_schedule_time(schedule_hours)
                app_state.auto.next_run_at = next_time.strftime("%H:%M")
                now = datetime.now(KST)
                wait_sec = max(0.0, (next_time - now).total_seconds())
                try:
                    await asyncio.sleep(wait_sec)
                except asyncio.CancelledError:
                    return
            first_run = False

            if not app_state.auto.enabled:
                return

            await _run_auto_cycle(schedule_hours)
    finally:
        app_state.auto.enabled = False
        app_state.auto.current_course = ""
        app_state.auto.current_lecture = ""
        app_state.auto.task = None
        app_state.auto.task_id = None


@router.get("/status")
async def auto_status():
    _require_auth()
    a = app_state.auto
    return {
        "enabled": a.enabled,
        "schedule_hours": a.schedule_hours,
        "current_course": a.current_course or None,
        "current_lecture": a.current_lecture or None,
        "processed_count": a.processed_count,
        "next_run_at": a.next_run_at or None,
        "error": a.error,
        "task_id": a.task_id,
    }


@router.post("/start")
async def auto_start(req: AutoStartRequest):
    _require_auth()

    hours = sorted(set(req.schedule_hours))
    if not hours or any(h < 0 or h > 23 for h in hours):
        raise HTTPException(status_code=422, detail="스케줄 시간은 0~23 사이 값이어야 합니다.")
    if len(hours) > 6:
        raise HTTPException(status_code=422, detail="스케줄은 최대 6회까지 설정할 수 있습니다.")

    if app_state.auto.enabled and app_state.auto.task and not app_state.auto.task.done():
        raise HTTPException(status_code=409, detail="이미 자동 모드가 실행 중입니다.")

    app_state.auto.enabled = True
    app_state.auto.schedule_hours = hours
    app_state.auto.processed_count = 0
    app_state.auto.error = None
    app_state.auto.next_run_at = ""

    async def run(managed: ManagedTask):
        managed.update(stage="auto_loop", message="자동 모드가 실행 중입니다.")
        await _auto_loop(hours)
        if app_state.auto.error:
            managed.update(status="failed", stage="error", error=app_state.auto.error)
        return {"processed_count": app_state.auto.processed_count}

    managed = task_manager.create("auto", run, metadata={"schedule_hours": hours})
    app_state.auto.task = managed.task
    app_state.auto.task_id = managed.id

    return {"started": True, "schedule_hours": hours, "task_id": managed.id}


@router.post("/stop")
async def auto_stop():
    _require_auth()
    app_state.auto.enabled = False
    if app_state.auto.task_id:
        await task_manager.cancel(app_state.auto.task_id)
    elif app_state.auto.task and not app_state.auto.task.done():
        app_state.auto.task.cancel()
        with suppress(Exception):
            await asyncio.wait_for(asyncio.shield(app_state.auto.task), timeout=3.0)
    app_state.auto.task = None
    app_state.auto.task_id = None
    app_state.auto.current_course = ""
    app_state.auto.current_lecture = ""
    return {"stopped": True}
