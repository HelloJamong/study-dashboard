from contextlib import asynccontextmanager

from backend.api.routes import auth, auto, courses, logs, player, settings, summaries, tasks
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src import db
    from src.config import Config

    db.init()
    Config.load()
    yield
    from backend.api.state import app_state

    if app_state.scraper:
        await app_state.scraper.close()


app = FastAPI(title="Study Helper API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(player.router, prefix="/api/player", tags=["player"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(auto.router, prefix="/api/auto", tags=["auto"])
app.include_router(summaries.router, prefix="/api/summaries", tags=["summaries"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
