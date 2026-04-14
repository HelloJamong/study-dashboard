"""구조화된 행위 로그 저장소.

웹 로그인/로그아웃, 설정 변경, 재생/다운로드 결과처럼 운영 중 추적이
필요한 이벤트를 SQLite `event_logs` 테이블에 남긴다.

로그 저장은 본 기능을 막지 않는 best-effort 정책이다. 공개 함수
`record_event()`는 내부 DB 오류가 발생해도 예외를 전파하지 않고 False를
반환한다.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from src import db
from src.config import KST

_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
_REDACTED = "[redacted]"
_SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "pwd",
    "token",
    "api_key",
    "apikey",
    "secret",
    "cookie",
    "authorization",
    "credential",
)


def event_timestamp(now: datetime | None = None) -> str:
    """로그 타임스탬프를 `YYYY-MM-DD HH:mm:ss` 형식으로 반환한다."""
    if now is None:
        now = datetime.now(KST)
    return now.astimezone(KST).strftime(_TIMESTAMP_FORMAT)


def is_sensitive_key(key: str) -> bool:
    """키 이름이 민감정보로 보이면 True."""
    normalized = key.lower().replace("-", "_")
    return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def mask_user_id(user_id: str | None) -> str | None:
    """로그인 실패 등에 사용할 사용자 ID 마스킹."""
    if not user_id:
        return None
    if len(user_id) <= 4:
        return "*" * len(user_id)
    return f"{user_id[:4]}{'*' * (len(user_id) - 4)}"


def sanitize_for_log(value: Any, *, key: str | None = None) -> Any:
    """로그 metadata에 저장하기 전 민감값을 재귀적으로 마스킹한다."""
    if key and is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return {str(k): sanitize_for_log(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_log(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize_for_log(v) for v in value]
    return value


def _metadata_to_json(metadata: dict[str, Any] | None) -> str:
    sanitized = sanitize_for_log(metadata or {})
    return json.dumps(sanitized, ensure_ascii=False, sort_keys=True)


def _insert_event(
    *,
    event_type: str,
    action: str,
    status: str,
    actor_user_id: str | None = None,
    session_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    course_id: str | None = None,
    course_name: str | None = None,
    lecture_title: str | None = None,
    lecture_url: str | None = None,
    week_label: str | None = None,
    message: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    log_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    event_id = uuid.uuid4().hex
    with db._connect() as conn:
        conn.execute(
            """
            INSERT INTO event_logs (
                event_id, created_at, actor_user_id, session_id, event_type,
                action, status, target_type, target_id, course_id, course_name,
                lecture_title, lecture_url, week_label, message, error_code,
                error_message, log_path, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_timestamp(),
                actor_user_id,
                session_id,
                event_type,
                action,
                status,
                target_type,
                target_id,
                course_id,
                course_name,
                lecture_title,
                lecture_url,
                week_label,
                message,
                error_code,
                error_message,
                log_path,
                _metadata_to_json(metadata),
            ),
        )
    return event_id


def record_event(**kwargs: Any) -> bool:
    """행위 로그를 저장한다. 저장 실패는 원 기능을 막지 않는다."""
    try:
        _insert_event(**kwargs)
        return True
    except Exception:
        return False


def list_events(
    *,
    event_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """최근 행위 로그를 조회한다."""
    safe_limit = max(1, min(limit, 200))
    clauses: list[str] = []
    params: list[Any] = []
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with db._connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, event_id, created_at, actor_user_id, session_id, event_type,
                   action, status, target_type, target_id, course_id, course_name,
                   lecture_title, lecture_url, week_label, message, error_code,
                   error_message, log_path, metadata_json
            FROM event_logs
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (*params, safe_limit),
        ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        raw_metadata = item.pop("metadata_json") or "{}"
        try:
            item["metadata"] = json.loads(raw_metadata)
        except json.JSONDecodeError:
            item["metadata"] = {}
        events.append(item)
    return events


def setting_snapshot(keys: list[str]) -> dict[str, str]:
    """설정 변경 로그용 현재 설정 snapshot. 민감값은 마스킹한다."""
    snapshot: dict[str, str] = {}
    for key in keys:
        if is_sensitive_key(key):
            snapshot[key] = _REDACTED if db.get(key) else ""
        else:
            snapshot[key] = db.get(key)
    return snapshot


def changed_keys(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """before/after 값이 달라진 key 목록."""
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def is_timestamp_format(value: str) -> bool:
    """테스트/검증용 타임스탬프 형식 확인."""
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value))
