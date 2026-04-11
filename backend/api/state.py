import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlaybackProgress:
    current: float = 0.0
    duration: float = 0.0
    ended: bool = False
    error: Optional[str] = None

    @property
    def progress_pct(self) -> float:
        if self.duration <= 0:
            return 0.0
        return min(100.0, self.current / self.duration * 100)


@dataclass
class AppState:
    scraper: object = None  # CourseScraper (순환 import 방지를 위해 Any)
    user_id: str = ""
    courses: list = field(default_factory=list)
    details: list = field(default_factory=list)
    is_playing: bool = False
    current_lecture_title: str = ""
    current_lecture_url: str = ""
    current_week_label: str = ""
    current_course_name: str = ""
    playback: PlaybackProgress = field(default_factory=PlaybackProgress)
    play_task: Optional[asyncio.Task] = None


app_state = AppState()
