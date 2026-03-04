from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import cv2
from app.state import processors

router = APIRouter()

def generate_frames(camera_id: str):
    proc = processors.get(camera_id)
    if not proc:
        return
    while True:
        frame = proc.get_frame()
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        # Без задержек – максимальная скорость отдачи кадров

@router.get("/{camera_id}")
async def video_stream(camera_id: str):
    if camera_id not in processors:
        raise HTTPException(status_code=404, detail="Camera not found")
    return StreamingResponse(generate_frames(camera_id),
                             media_type="multipart/x-mixed-replace; boundary=frame")