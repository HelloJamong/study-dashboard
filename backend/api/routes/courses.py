from fastapi import APIRouter, HTTPException

from backend.api.state import app_state

router = APIRouter()


def _require_auth():
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


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
