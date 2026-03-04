from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.state import processors
from app.config import config
import asyncio

router = APIRouter()

@router.get("/cameras")
async def get_cameras():
    return [{"id": cam["id"], "name": cam["name"], "capacity": cam["capacity"]} for cam in config["cameras"]]

@router.get("/status")
async def get_status():
    result = []
    for cam_id, proc in processors.items():
        status = proc.get_status()
        result.append(status)
    return result

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = [proc.get_status() for proc in processors.values()]
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Client disconnected")