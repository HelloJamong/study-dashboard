"""웹/CLI에서 재사용 가능한 강의 다운로드 파이프라인."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.config import normalize_download_rule
from src.converter.audio_converter import convert_to_mp3
from src.downloader.video_downloader import download_video_with_browser, extract_video_url, make_filepath

StageCallback = Callable[[str, str, float | None], None]
ProgressCallback = Callable[[int, int], None]

_MAX_URL_RETRIES = 3
_RETRY_WAIT_SECONDS = 10


class DownloadUnsupportedError(RuntimeError):
    """LMS 강의 유형상 다운로드를 지원하지 않을 때 발생한다."""


def build_download_paths(
    *,
    download_dir: str,
    course_name: str,
    week_label: str,
    lecture_title: str,
) -> tuple[Path, Path]:
    """다운로드 base dir과 mp4 저장 경로를 안전하게 계산한다."""
    base_dir = Path(download_dir).expanduser().resolve()
    mp4_path = (base_dir / make_filepath(course_name, week_label, lecture_title)).resolve()
    if not mp4_path.is_relative_to(base_dir):
        raise ValueError("잘못된 다운로드 경로가 감지되었습니다.")
    return base_dir, mp4_path


async def download_lecture_media(
    *,
    page: Any,
    lecture_url: str,
    lecture_title: str,
    week_label: str,
    course_name: str,
    download_dir: str,
    rule: str,
    on_stage: StageCallback | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """강의 영상을 설정 규칙에 따라 mp4/mp3/both로 저장한다."""
    normalized_rule = normalize_download_rule(rule)
    base_dir, mp4_path = build_download_paths(
        download_dir=download_dir,
        course_name=course_name,
        week_label=week_label,
        lecture_title=lecture_title,
    )

    def stage(name: str, message: str, progress_pct: float | None = None) -> None:
        if on_stage:
            on_stage(name, message, progress_pct)

    if "learningx" in lecture_url:
        raise DownloadUnsupportedError("이 강의는 다운로드가 지원되지 않는 형식입니다.")

    stage("extracting_url", "영상 URL을 추출하는 중입니다.", 5)
    video_url = None
    for attempt in range(1, _MAX_URL_RETRIES + 1):
        video_url = await extract_video_url(page, lecture_url)
        if video_url:
            break
        if attempt < _MAX_URL_RETRIES:
            stage(
                "retrying_url",
                f"영상 URL 추출 실패. 재시도 대기 중입니다. ({attempt}/{_MAX_URL_RETRIES})",
                5,
            )
            await asyncio.sleep(_RETRY_WAIT_SECONDS)

    if not video_url:
        raise RuntimeError("영상 URL을 찾지 못했습니다. (3회 시도)")

    stage("downloading", "mp4 파일을 다운로드하는 중입니다.", 10)

    def progress(downloaded: int, total: int) -> None:
        if total > 0:
            pct = 10 + (downloaded / total * 75)
            stage("downloading", "mp4 파일을 다운로드하는 중입니다.", pct)
        if on_progress:
            on_progress(downloaded, total)

    await download_video_with_browser(page, video_url, mp4_path, on_progress=progress)

    files: list[dict[str, str]] = []
    mp3_path: Path | None = None
    if normalized_rule in {"mp4", "both"}:
        files.append({"type": "mp4", "path": str(mp4_path)})

    if normalized_rule in {"mp3", "both"}:
        stage("converting", "mp3 파일로 변환하는 중입니다.", 90)
        loop = asyncio.get_running_loop()
        mp3_path = await loop.run_in_executor(None, convert_to_mp3, mp4_path)
        files.append({"type": "mp3", "path": str(mp3_path)})
        if normalized_rule == "mp3":
            mp4_path.unlink(missing_ok=True)

    stage("completed", "다운로드가 완료되었습니다.", 100)
    return {
        "download_rule": normalized_rule,
        "download_dir": str(base_dir),
        "files": files,
    }
