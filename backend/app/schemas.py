from pydantic import BaseModel
from typing import Optional

class CameraStatus(BaseModel):
    camera_id: str
    vehicle_count: int
    free_spots: int
    capacity: int
    is_streaming: bool = True