from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.routes import stream, data
from app.config import config
from app.video_processor import VideoProcessor
from app.state import processors

app = FastAPI(title="SpotCar API")

# Разрешаем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    for cam in config["cameras"]:
        proc = VideoProcessor(cam)
        proc.start()
        processors[cam["id"]] = proc

@app.on_event("shutdown")
async def shutdown():
    for proc in processors.values():
        proc.stop()

# Подключаем роуты API
app.include_router(stream.router, prefix="/stream", tags=["stream"])
app.include_router(data.router, prefix="/data", tags=["data"])

# Раздаём статические файлы фронтенда, если папка существует
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

@app.get("/")
def root():
    return {"message": "SpotCar API (frontend доступен по /)"}