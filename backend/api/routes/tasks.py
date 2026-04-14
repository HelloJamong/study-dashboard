"""공통 백그라운드 태스크 상태 API."""

from backend.api.state import app_state
from backend.api.task_manager import ManagedTask, task_manager
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src import event_log
from src.config import Config

router = APIRouter()


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


class DownloadTaskRequest(BaseModel):
    course_id: str
    lecture_url: str
    lecture_title: str
    week_label: str = ""


def _find_course(course_id: str):
    return next((course for course in app_state.courses if course.id == course_id), None)


@router.post("/download")
async def start_download(req: DownloadTaskRequest):
    _require_auth()
    if Config.DOWNLOAD_ENABLED != "true":
        raise HTTPException(status_code=409, detail="설정에서 영상 다운로드를 먼저 활성화하세요.")
    if app_state.is_playing:
        raise HTTPException(status_code=409, detail="재생 중에는 다운로드를 시작할 수 없습니다.")
    if app_state.auto.enabled:
        raise HTTPException(status_code=409, detail="자동 모드 실행 중에는 다운로드를 시작할 수 없습니다.")

    course = _find_course(req.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="과목을 찾을 수 없습니다.")

    from src.downloader.pipeline import DownloadUnsupportedError, download_lecture_media

    async def run(managed: ManagedTask):
        def on_stage(stage: str, message: str, progress_pct: float | None = None) -> None:
            managed.update(stage=stage, message=message, progress_pct=progress_pct)

        try:
            result = await download_lecture_media(
                page=app_state.scraper._page,
                lecture_url=req.lecture_url,
                lecture_title=req.lecture_title,
                week_label=req.week_label,
                course_name=course.long_name,
                download_dir=Config.get_download_dir(),
                rule=Config.get_download_rule(),
                stt_enabled=Config.STT_ENABLED == "true",
                stt_model=Config.WHISPER_MODEL or "base",
                stt_language=Config.STT_LANGUAGE or "",
                delete_audio_after_stt=Config.STT_DELETE_AUDIO_AFTER_TRANSCRIBE == "true",
                ai_enabled=Config.AI_ENABLED == "true",
                ai_agent=Config.AI_AGENT or "gemini",
                ai_api_key=Config.GOOGLE_API_KEY,
                ai_model=Config.GEMINI_MODEL,
                summary_prompt_template=Config.get_summary_prompt_template(),
                summary_prompt_extra=Config.SUMMARY_PROMPT_EXTRA,
                delete_text_after_summary=Config.SUMMARY_DELETE_TEXT_AFTER_SUMMARIZE == "true",
                on_stage=on_stage,
            )
            stt_result = result.get("stt") or {}
            if stt_result.get("status") == "completed":
                event_log.record_event(
                    event_type="stt",
                    action="transcribe_complete",
                    status="success",
                    actor_user_id=app_state.user_id or None,
                    target_type="lecture",
                    course_id=req.course_id,
                    course_name=course.long_name,
                    lecture_title=req.lecture_title,
                    lecture_url=req.lecture_url,
                    week_label=req.week_label,
                    message="STT 변환이 완료되었습니다.",
                    metadata={"task_id": managed.id, "stt": stt_result},
                )
            summary_result = result.get("summary") or {}
            if summary_result.get("status") == "completed":
                event_log.record_event(
                    event_type="summary",
                    action="summary_complete",
                    status="success",
                    actor_user_id=app_state.user_id or None,
                    target_type="lecture",
                    course_id=req.course_id,
                    course_name=course.long_name,
                    lecture_title=req.lecture_title,
                    lecture_url=req.lecture_url,
                    week_label=req.week_label,
                    message="AI 요약이 완료되었습니다.",
                    metadata={"task_id": managed.id, "summary": summary_result},
                )
            event_log.record_event(
                event_type="download",
                action="download_complete",
                status="success",
                actor_user_id=app_state.user_id or None,
                target_type="lecture",
                course_id=req.course_id,
                course_name=course.long_name,
                lecture_title=req.lecture_title,
                lecture_url=req.lecture_url,
                week_label=req.week_label,
                message="다운로드가 완료되었습니다.",
                metadata={"task_id": managed.id, "result": result},
            )
            return result
        except DownloadUnsupportedError as e:
            managed.update(status="failed", stage="unsupported", error=str(e), message=str(e))
            event_log.record_event(
                event_type="download",
                action="download_unsupported",
                status="failed",
                actor_user_id=app_state.user_id or None,
                target_type="lecture",
                course_id=req.course_id,
                course_name=course.long_name,
                lecture_title=req.lecture_title,
                lecture_url=req.lecture_url,
                week_label=req.week_label,
                error_code="unsupported",
                error_message=str(e),
                metadata={"task_id": managed.id},
            )
            return {}
        except Exception as e:
            if managed.stage == "transcribing":
                event_log.record_event(
                    event_type="stt",
                    action="transcribe_failed",
                    status="failed",
                    actor_user_id=app_state.user_id or None,
                    target_type="lecture",
                    course_id=req.course_id,
                    course_name=course.long_name,
                    lecture_title=req.lecture_title,
                    lecture_url=req.lecture_url,
                    week_label=req.week_label,
                    error_code=type(e).__name__,
                    error_message=str(e),
                    metadata={"task_id": managed.id},
                )
            if managed.stage == "summarizing":
                event_log.record_event(
                    event_type="summary",
                    action="summary_failed",
                    status="failed",
                    actor_user_id=app_state.user_id or None,
                    target_type="lecture",
                    course_id=req.course_id,
                    course_name=course.long_name,
                    lecture_title=req.lecture_title,
                    lecture_url=req.lecture_url,
                    week_label=req.week_label,
                    error_code=type(e).__name__,
                    error_message=str(e),
                    metadata={"task_id": managed.id},
                )
            event_log.record_event(
                event_type="download",
                action="download_failed",
                status="failed",
                actor_user_id=app_state.user_id or None,
                target_type="lecture",
                course_id=req.course_id,
                course_name=course.long_name,
                lecture_title=req.lecture_title,
                lecture_url=req.lecture_url,
                week_label=req.week_label,
                error_code=type(e).__name__,
                error_message=str(e),
                metadata={"task_id": managed.id},
            )
            raise

    managed = task_manager.create(
        "download",
        run,
        metadata={
            "course_id": req.course_id,
            "course_name": course.long_name,
            "lecture_title": req.lecture_title,
            "week_label": req.week_label,
            "download_rule": Config.get_download_rule(),
            "stt_enabled": Config.STT_ENABLED,
            "stt_delete_audio_after_transcribe": Config.STT_DELETE_AUDIO_AFTER_TRANSCRIBE,
            "ai_enabled": Config.AI_ENABLED,
            "summary_delete_text_after_summarize": Config.SUMMARY_DELETE_TEXT_AFTER_SUMMARIZE,
        },
    )
    event_log.record_event(
        event_type="download",
        action="download_start",
        status="started",
        actor_user_id=app_state.user_id or None,
        target_type="lecture",
        course_id=req.course_id,
        course_name=course.long_name,
        lecture_title=req.lecture_title,
        lecture_url=req.lecture_url,
        week_label=req.week_label,
        message="다운로드를 시작했습니다.",
        metadata={
            "task_id": managed.id,
            "download_rule": Config.get_download_rule(),
            "stt_enabled": Config.STT_ENABLED,
        },
    )
    return {"started": True, "task_id": managed.id}


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
    task_before = task_manager.get(task_id)
    cancelled = await task_manager.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    task = task_manager.get(task_id)
    if task_before and task_before.kind == "download":
        event_log.record_event(
            event_type="download",
            action="download_cancel",
            status="cancelled",
            actor_user_id=app_state.user_id or None,
            course_id=task_before.metadata.get("course_id"),
            course_name=task_before.metadata.get("course_name"),
            lecture_title=task_before.metadata.get("lecture_title"),
            week_label=task_before.metadata.get("week_label"),
            message="다운로드 취소 요청",
            metadata={"task_id": task_id},
        )
    return task.to_dict() if task else {"cancelled": True}
