from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.sessions import SessionMiddleware
import os
from app.routes import stream, data
from app.auth import router as auth_router
from app.config import config
from app.video_processor import VideoProcessor
from app.state import processors
from app.database import init_db


app = FastAPI(title="SpotCar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-me")
)

@app.on_event("startup")
async def startup():
    init_db()


    for cam in config["cameras"]:
        proc = VideoProcessor(cam)
        proc.start()
        processors[cam["id"]] = proc


@app.on_event("shutdown")
async def shutdown():
    for proc in processors.values():
        proc.stop()


app.include_router(stream.router, prefix="/stream", tags=["stream"])
app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])


frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


@app.get("/")
def root():
    return {"message": "SpotCar API "}