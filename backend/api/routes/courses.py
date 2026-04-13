from collections import Counter
from pathlib import Path

from backend.api.state import app_state
from fastapi import APIRouter, HTTPException

router = APIRouter()


def _require_auth():
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


def _summaries_dir() -> Path:
    """요약 저장 디렉터리 — Docker /data 우선, 없으면 로컬 data/ 사용."""
    for candidate in (Path("/data/summaries"), Path("data/summaries")):
        if candidate.parent.exists():
            return candidate
    return Path("data/summaries")


@router.get("")
async def get_courses():
    _require_auth()

    if not app_state.courses:
        courses = await app_state.scraper.fetch_courses()
        details = await app_state.scraper.fetch_all_details(courses, concurrency=3)
        app_state.courses = courses
        app_state.details = details

    result = []
    for i, course in enumerate(app_state.courses):
        detail = app_state.details[i] if i < len(app_state.details) else None
        result.append(
            {
                "id": course.id,
                "name": course.long_name,
                "term": course.term,
                "total_videos": detail.total_video_count if detail else 0,
                "pending_videos": detail.pending_video_count if detail else 0,
            }
        )
    return result


@router.get("/stats")
async def get_stats():
    _require_auth()

    total = sum(
        d.total_video_count for d in app_state.details if d
    )
    completed = sum(
        d.total_video_count - d.pending_video_count for d in app_state.details if d
    )
    return {"total_videos": total, "completed_videos": completed}


@router.get("/terms")
async def get_terms():
    _require_auth()

    # 과목 목록에서 가장 많이 등장하는 term = 현재 학기
    current_term = ""
    if app_state.courses:
        terms = [c.term for c in app_state.courses if c.term]
        if terms:
            current_term = Counter(terms).most_common(1)[0][0]

    # 요약 마크다운이 저장된 과거 학기 스캔 (현재 학기 제외)
    sdir = _summaries_dir()
    past_terms: list[str] = []
    if sdir.exists():
        past_terms = sorted(
            [d.name for d in sdir.iterdir() if d.is_dir() and d.name != current_term],
            reverse=True,
        )

    return {"current_term": current_term, "past_terms": past_terms}


@router.post("/refresh")
async def refresh_courses():
    _require_auth()

    app_state.courses = []
    app_state.details = []
    courses = await app_state.scraper.fetch_courses()
    details = await app_state.scraper.fetch_all_details(courses, concurrency=3)
    app_state.courses = courses
    app_state.details = details
    return {"success": True, "count": len(courses)}


@router.get("/{course_id}")
async def get_course_detail(course_id: str):
    _require_auth()

    idx = next((i for i, c in enumerate(app_state.courses) if c.id == course_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="과목을 찾을 수 없습니다.")

    course = app_state.courses[idx]
    detail = app_state.details[idx] if idx < len(app_state.details) else None
    if not detail:
        raise HTTPException(status_code=404, detail="강의 정보를 불러오지 못했습니다.")

    weeks = []
    for week in detail.weeks:
        lectures = []
        for lec in week.lectures:
            lectures.append(
                {
                    "title": lec.title,
                    "url": lec.item_url,
                    "full_url": lec.full_url,
                    "type": lec.lecture_type.value,
                    "week_label": lec.week_label,
                    "duration": lec.duration,
                    "attendance": lec.attendance,
                    "completion": lec.completion,
                    "is_video": lec.is_video,
                    "needs_watch": lec.needs_watch,
                }
            )
        weeks.append(
            {
                "title": week.title,
                "week_number": week.week_number,
                "lectures": lectures,
                "pending_count": week.pending_count,
            }
        )

    return {
        "id": course.id,
        "name": course.long_name,
        "term": course.term,
        "professors": detail.professors,
        "weeks": weeks,
    }
