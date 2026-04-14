# Changelog

## [v26.04.07] - 2026-04-14

### Background Task 공통화 및 프론트 모듈 분리

#### 추가
- **공통 백그라운드 태스크 관리자** (`backend/api/task_manager.py`)
  - `ManagedTask` 상태 모델 추가: `queued` / `running` / `completed` / `failed` / `cancelled`
  - 작업별 `stage`, `message`, `progress_pct`, `result`, `error`, `metadata` 추적 지원
  - `TaskManager.create()`, `cancel()`, `get()`, `list()`로 장시간 작업 실행/취소/조회 흐름 공통화
- **공통 태스크 상태 API** (`backend/api/routes/tasks.py`)
  - `GET /api/tasks` — 등록된 백그라운드 작업 목록 조회
  - `GET /api/tasks/{task_id}` — 단일 작업 상태 조회
  - `POST /api/tasks/{task_id}/cancel` — 작업 취소 요청
- **요약 조회 API** (`backend/api/routes/summaries.py`, `backend/api/summary_store.py`)
  - `GET /api/summaries/{summary_id}` 추가
  - `data/summaries/{term}/{course}/{week}/{lecture}.md` 형식의 신규 요약 저장 위치 조회 지원
  - 기존 다운로드 폴더의 `{lecture}_summarized.txt` 요약 파일도 fallback으로 조회
  - summary id는 파일 경로를 직접 노출하지 않도록 URL-safe base64로 인코딩
- **강의 상세 요약 메타데이터** (`backend/api/routes/courses.py`)
  - 강의별 `has_summary`, `summary_id`, `summary` 필드 추가
  - 완료된 강의에 요약 파일이 있으면 프론트에서 “요약 내용 보기” 버튼을 표시할 수 있도록 연결
- **요약 상세 화면** (`frontend/index.html`, `frontend/js/app.js`)
  - 강의 상세 화면에서 완료+요약 존재 강의에 “요약 내용 보기” 버튼 표시
  - 요약 상세 페이지에서 AI 요약 내용을 마크다운 스타일로 렌더링
  - 마크다운 렌더러는 DOM 생성 + `textContent` 기반으로 동작해 요약 본문 HTML 주입을 방지

#### 변경
- **웹 재생/자동 모드 태스크 연결** (`backend/api/routes/player.py`, `backend/api/routes/auto.py`)
  - `asyncio.create_task()` 직접 호출을 `task_manager.create()` 기반으로 전환
  - 재생 시작/자동 모드 시작 응답에 `task_id` 반환
  - `/api/player/status`, `/api/auto/status`에서 현재 연결된 task id 노출
  - 로그아웃/중지 시 공통 task manager cancellation 경로 사용
- **프론트 구조 결정: vanilla 유지 + ES module 분리**
  - 기존 단일 `frontend/index.html` inline script를 `frontend/js/` 모듈로 분리
  - `frontend/js/api.js`: API 호출/timeout 처리
  - `frontend/js/utils.js`: DOM selector, escape, time formatting
  - `frontend/js/markdown.js`: 안전한 마크다운 렌더링
  - `frontend/js/state.js`: 전역 앱 상태
  - `frontend/js/app.js`: 페이지 라우팅/이벤트 바인딩/화면 로직
  - `frontend/Dockerfile`, `docker-compose.yml`에 `/js` 정적 파일 배포/개발 마운트 추가
- **강의 상세 UX 개선**
  - 강의 목록 하단 패널 대신 별도 강의 상세 페이지로 전환
  - “강의 목록으로” / “주차별 강의로” 복귀 동선 추가
  - 과목 카드에 키보드 접근성(`role="button"`, `tabindex`) 보강

#### 테스트
- **`tests/test_task_manager.py`**
  - 공통 task manager 완료/취소 상태 전이 검증
- **`tests/test_web_summaries.py`**
  - 강의 상세 API의 요약 파일 감지 검증
  - 요약 조회 API의 마크다운 읽기 검증
- 기존 웹 auth/player 테스트의 app_state reset 범위를 task id/auto task까지 확장

#### 검증
- `node --check frontend/js/*.js` — 통과
- `uv run pytest` — 45 passed
- `uv run ruff check .` — All checks passed

## [v26.04.06] - 2026-04-14

### OpenAI 제거 — Gemini 단일 요약 엔진으로 통합

#### 변경
- **`src/summarizer/summarizer.py`** — `_summarize_openai()` 함수 및 `elif agent == "openai"` 분기 제거, docstring Gemini 전용으로 수정
- **`src/config.py`** — `OPENAI_API_KEY` 클래스 속성·로드·저장 로직 제거, `save_settings()`의 ai_agent 분기를 Gemini 단일 경로로 단순화
- **`src/ui/auto.py`** / **`src/ui/download.py`** — `Config.OPENAI_API_KEY` 참조 제거, `api_key = Config.GOOGLE_API_KEY` / `model = Config.GEMINI_MODEL` 직접 사용
- **`backend/api/routes/settings.py`** — `_SENSITIVE`에서 `OPENAI_API_KEY` 제거, `SettingsUpdate` 모델에서 `OPENAI_API_KEY` 필드 제거
- **`frontend/index.html`** — AI 에이전트 select에서 OpenAI 옵션 제거, OpenAI API Key 입력 필드 제거
- **`tests/test_summarizer.py`** — `test_summarize_openai_path` 테스트 제거
- **`pyproject.toml`** — `openai>=1.0.0` 의존성 제거
- **`uv.lock`** — openai 패키지 및 관련 의존성 제거 (69 패키지로 축소)

## [v26.04.05] - 2026-04-14

### 강의 목록 학기 선택 UI 추가

#### 추가
- **`GET /api/courses/terms`** (`backend/api/routes/courses.py`)
  - 현재 학기: 로드된 과목 목록에서 최빈 term 자동 감지
  - 과거 학기: `data/summaries/{term}/` 디렉터리 스캔 — 요약 마크다운이 저장된 학기만 반환
  - 현재 과목이 미로드 상태면 `current_term`은 빈 문자열 반환 (클라이언트 폴백)
- **학기 선택 탭 UI** (`frontend/index.html`)
  - 강의 목록 페이지 최상단에 학기 탭 영역 추가 (`#term-selector`)
  - 과거 학기 요약 기록이 없으면 탭 영역 자체를 숨김 — 현재 UX 변화 없음
  - 과거 학기가 있으면 인디고 pill 탭으로 현재/과거 학기 선택 가능
  - 학기 전환 시 강의 상세 패널 자동 닫힘
- **`loadTerms()` / `switchTerm()` / `loadSummaryTerm()`** (`frontend/index.html`)
  - `loadTerms()`: terms API 호출 후 탭 동적 생성
  - `switchTerm(term)`: 탭 활성 상태 갱신, 현재 학기면 `loadCourses()` / 과거면 `loadSummaryTerm()`
  - `loadSummaryTerm(term)`: 요약 기능 구현 전 안내 placeholder 표시 — 추후 요약 API 연결 예정

## [v26.04.04] - 2026-04-14

### 대시보드 UX 개선 및 보안 강화

#### 수정
- **대시보드 통계 초기 로딩 문제** (`frontend/index.html`)
  - 로그인 직후 대시보드 진입 시 통계가 0/0으로 잘못 표시되던 문제 수정
  - `loadStats()` 호출 시 백엔드 `details`가 비어있으면 `GET /api/courses`를 먼저 호출해 채운 뒤 통계를 재조회하도록 개선
  - 이미 과목이 로드된 세션에서는 추가 요청 없이 즉시 통계 갱신 유지
- **로그아웃 버튼 가시성** (`frontend/index.html`)
  - 페이지 내용이 길어질 때 로그아웃 버튼이 화면 밖으로 밀려 보이지 않던 문제 수정
  - `#app-shell`을 `min-h-screen` → `h-screen overflow-hidden`으로, `aside`에 `overflow-y-auto` 추가
  - 사이드바가 뷰포트 내에서 독립 스크롤하므로 어느 페이지에서도 로그아웃 버튼 항상 접근 가능
- **로그아웃 시 로그인 폼 초기화** (`frontend/index.html`)
  - `showLogin()` 진입 시 학번·비밀번호 입력창과 오류 메시지를 초기화
  - 로그아웃 후 잔류 자격증명으로 재로그인 가능하던 문제 수정
  - 세션 만료 등 모든 로그인 화면 전환 경로에 일괄 적용
- **Settings API 인증 추가** (`backend/api/routes/settings.py`)
  - `GET /api/settings`, `PUT /api/settings` 모두 `_require_auth()` 추가
  - 비로그인 상태에서 설정 조회/변경 시 401 반환
- **Auto status API 인증 추가** (`backend/api/routes/auto.py`)
  - `GET /api/auto/status`에 `_require_auth()` 추가 (start/stop은 기존에 이미 인증 적용)
  - `GET /api/player/status`는 로컬 단일 사용자 서비스 특성상 공개 유지
- **프론트 XSS/HTML Injection 방어** (`frontend/index.html`)
  - `esc()` 헬퍼 추가 — `div.textContent` 기반 HTML 특수문자 이스케이프
  - `renderCourseCards()`: `course.name`, `course.term` → `esc()` 적용
  - `loadCourseDetail()`: `week.title` → `esc()`, 강의 row `data-*` 속성은 `element.dataset` 직접 할당
  - `lec.title`, `lec.duration` → `textContent` 직접 할당, `lec.completion` → 화이트리스트 검증
  - 오류 메시지 div의 `err.message` → `esc()` 적용

## [v26.04.03] - 2026-04-03

### 웹 재생 안정성 및 피드백 보강

#### 추가
- **웹 재생 상태 확장** (`backend/api/state.py`)
  - `PlaybackProgress.status`: `idle` / `playing` / `completed` / `error` / `stopped` 상태 구분
  - `PlaybackProgress.log_path`: 웹 재생 실패 시 저장된 진단 로그 경로 노출
- **웹 재생 결과 처리 강화** (`backend/api/routes/player.py`)
  - `play_lecture()` 반환값을 검사해 완료/오류/중지 상태를 명확히 반영
  - 재생 실패 시 `logs/*_web_play.log` 진단 로그 저장
  - 재생 완료 시 캐시된 강의 항목의 `completion`을 즉시 `completed`로 갱신
- **대시보드 재생 피드백 UI** (`frontend/index.html`)
  - 재생 완료/중지/실패 메시지 표시
  - 실패 시 `/api/player/status`의 `error`와 `log_path` 표시
  - 재생 완료 감지 후 통계와 강의 목록 캐시 자동 갱신
- **웹 player route 회귀 테스트** (`tests/test_web_player.py`)
  - 재생 완료 후 강의 completion 갱신 검증
  - 재생 오류가 status/error/log_path에 유지되는지 검증
- **로그인 실패/지연 처리 보강** (`backend/api/routes/auth.py`, `frontend/index.html`)
  - 백엔드 로그인 시도에 45초 제한을 적용해 Playwright 로그인 대기가 무한히 이어지지 않도록 함
  - cancellation에 즉시 응답하지 않는 Playwright 작업도 timeout 시 사용자 응답을 막지 않도록 처리
  - 잘못된 계정/비밀번호 입력 시 SSO 로그인 폼 잔류, alert, 오류 문구를 짧은 폴링으로 감지해 실패 메시지를 더 빠르게 반환 (`src/auth/login.py`)
  - 로그인 성공/실패 판정 단위 테스트 추가 (`tests/test_login.py`) — 폼 잔류 시 빠른 실패, URL 전환 시 성공 시나리오 검증
  - 프론트 로그인 요청에 60초 timeout을 적용하고 실패/timeout 메시지를 로그인 카드에 표시
  - 학번/비밀번호 미입력 시 즉시 경고 메시지 표시
- **로컬 HTTPS 지원** (`frontend/nginx.conf`, `docker-compose.yml`)
  - nginx가 443/TLS를 직접 처리하고 `http://localhost:3000`을 `https://localhost:3443`으로 리다이렉트
  - backend 포트 `8000`은 로컬 호스트에만 바인딩해 브라우저 트래픽은 nginx HTTPS 프록시를 거치도록 조정
  - 최소 보안 헤더(HSTS, nosniff, SAMEORIGIN, Referrer-Policy) 추가
  - stale inline JS 캐시 방지를 위해 정적 응답에 `Cache-Control: no-store` 적용
- **로컬 인증서 생성 도구/문서**
  - `scripts/generate-local-cert.sh`: self-signed localhost 인증서 생성
  - `docs/https-local.md`: HTTPS 실행 및 인증서 신뢰 안내
  - `certs/.gitkeep`: 인증서 디렉터리만 추적하고 실제 인증서/키는 gitignore로 제외

#### 변경
- `POST /api/player/stop`에 로그인 상태 검사를 추가해 비인증 중지 요청을 차단
- backend/test 코드의 Ruff 지적 사항 정리
  - import 정렬
  - `HTTPException` 재발생 원인 명시 (`from None` / `from e`)
  - `Optional[...]` 타입 표기를 `... | None`으로 변경
  - 미사용 import 제거
- `docs/web-completeness-checklist.md`의 완료 항목을 체크 및 취소선으로 표시
- 로컬 HTTPS 인증서 실파일(`certs/local.crt`, `certs/local.key`)을 git 대상에서 제외

#### 검증
- `uv run pytest` — 41 passed
- `uv run ruff check .` — All checks passed
- FastAPI smoke 확인
  - `GET /api/health` → 200
  - `GET /api/auth/status` → 200
  - `GET /api/player/status` → 200
  - 비로그인 `POST /api/player/stop` → 401
  - nginx 설정 검증(`nginx -t`) → successful
  - `docker compose build frontend` → successful

#### 남은 확인
- 실제 LMS 계정으로 재생 성공/실패/중지 케이스 수동 검증 필요
- 브라우저에서 self-signed 인증서 경고 수락 또는 trust store 등록 필요
- 재생 완료 후 LMS 서버 출석 반영까지 실제 확인 필요

---

## [v26.04.02] - 2026-04-02

### 웹 대시보드 (Docker 풀스택 구성)

#### 추가
- **FastAPI 백엔드** (`backend/`)
  - `backend/main.py`: FastAPI 앱 진입점, 앱 시작 시 DB 초기화 및 `Config.load()` 호출
  - `backend/api/state.py`: 전역 앱 상태 (Playwright 세션, 재생 상태)
  - `backend/api/routes/auth.py`: `POST /api/auth/login|logout`, `GET /api/auth/status`
  - `backend/api/routes/courses.py`: `GET /api/courses`, `/api/courses/{id}`, `/api/courses/stats`, `POST /api/courses/refresh`
  - `backend/api/routes/player.py`: `POST /api/player/play|stop`, `GET /api/player/status`
  - `backend/api/routes/settings.py`: `GET|PUT /api/settings`
- **nginx 프론트엔드** (`frontend/`)
  - `frontend/index.html`: SPA 웹 대시보드 (로그인 / 대시보드 / 강의목록 / 설정)
  - `frontend/nginx.conf`: 정적 파일 서빙 + `/api/*` → 백엔드 프록시
  - `frontend/Dockerfile`: nginx:alpine 기반
- **Docker Compose 풀스택 구성** (`docker-compose.yml`)
  - `backend`: FastAPI + Playwright, 소스 볼륨 마운트 + `--reload` 핫 리로드
  - `frontend`: nginx, HTML/nginx.conf 볼륨 마운트로 재빌드 없이 즉시 반영
- **의존성 추가** (`pyproject.toml`): `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`
- `uv.lock` 재생성

#### 변경
- `backend/Dockerfile`: ENTRYPOINT/CMD 분리 — `docker-compose.yml`의 `command:`로 오버라이드 가능
- 루트 `Dockerfile` (TUI 전용) 제거 — 웹 대시보드로 대체

---

## [v26.04.01] - 2026-04-01

### 초기 구성

study-helper(HelloJamong/study-helper) 프로젝트에서 마이그레이션.

### 추가
- **SQLite 기반 설정 저장소** (`src/db.py`)
  - 기존 `.env` 파일 방식에서 `data/app.db`로 전환
  - `get / set / set_many` key-value API
  - `migrate_from_env()`: 기존 `.env` 보유 시 최초 실행 시 자동 마이그레이션
- **`Config.load()`** (`src/config.py`)
  - 클래스 속성을 앱 시작 시 DB에서 일괄 로드하는 명시적 초기화 메서드 추가
  - `python-dotenv` 의존성 제거 (`pyproject.toml`)
- **텔레그램 알림** (`src/notifier/`)
  - 재생 완료·실패 알림 (`telegram_notifier.py`)
  - 마감 임박 항목 감지 및 알림 (`deadline_checker.py`)
- **자동 모드** (`src/ui/auto.py`): 미완료 강의 일괄 재생
- **버전 체크** (`src/updater.py`): 과목 로딩과 병렬로 GitHub 최신 버전 확인
- **STT 엔진**: faster-whisper (CTranslate2 기반, torch 불필요)
- **GitHub Actions 워크플로우** (CI, Docker 릴리즈) — 재건 중 자동 실행 비활성화
