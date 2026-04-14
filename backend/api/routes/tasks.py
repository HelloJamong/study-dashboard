"""공통 백그라운드 태스크 상태 API."""

from backend.api.state import app_state
from backend.api.task_manager import ManagedTask, task_manager
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
            return await download_lecture_media(
                page=app_state.scraper._page,
                lecture_url=req.lecture_url,
                lecture_title=req.lecture_title,
                week_label=req.week_label,
                course_name=course.long_name,
                download_dir=Config.get_download_dir(),
                rule=Config.get_download_rule(),
                on_stage=on_stage,
            )
        except DownloadUnsupportedError as e:
            managed.update(status="failed", stage="unsupported", error=str(e), message=str(e))
            return {}

    managed = task_manager.create(
        "download",
        run,
        metadata={
            "course_id": req.course_id,
            "course_name": course.long_name,
            "lecture_title": req.lecture_title,
            "week_label": req.week_label,
            "download_rule": Config.get_download_rule(),
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
    cancelled = await task_manager.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    task = task_manager.get(task_id)
    return task.to_dict() if task else {"cancelled": True}
