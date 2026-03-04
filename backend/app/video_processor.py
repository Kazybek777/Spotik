import cv2
import numpy as np
from ultralytics import YOLO
from threading import Thread, Lock
from queue import Queue
import time
from pathlib import Path

class VideoProcessor:
    def __init__(self, camera_config):
        self.camera_id = camera_config["id"]
        self.source = camera_config["source"]
        self.capacity = camera_config["capacity"]
        self.lines = camera_config["lines"]
        self.direction = camera_config.get("direction", "horizontal")

        weights_path = Path(__file__).parent.parent / "weights" / "yolov8n.pt"
        self.model = YOLO(str(weights_path))

        self.cap = None
        self.running = False
        self.thread = None
        self.lock = Lock()
        self.frame_queue = Queue(maxsize=2)
        self.last_frame = None

        # Для подсчёта машин
        self.vehicle_count = 0
        self.tracked_objects = {}

        self.frame_skip = 2
        self.frame_counter = 0

        self.init_video()

    def init_video(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {self.source}")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = Thread(target=self._process, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()

    def _process(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            self.frame_counter += 1
            if self.frame_counter % (self.frame_skip + 1) == 0:
                results = self.model.track(frame, persist=True, classes=[2,3,5,7], verbose=False)
                if results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)
                    for box, track_id in zip(boxes, track_ids):
                        x1, y1, x2, y2 = box
                        centroid = ((x1 + x2) // 2, (y1 + y2) // 2)

                        self._check_lines(track_id, centroid)

                        self.tracked_objects[track_id] = centroid

            self._draw_lines(frame)
            cv2.putText(frame, f"Count: {self.vehicle_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            with self.lock:
                if self.frame_queue.full():
                    self.frame_queue.get()
                self.frame_queue.put(frame)
                self.last_frame = frame

    def _check_lines(self, track_id, current_centroid):
        prev_centroid = self.tracked_objects.get(track_id)
        if prev_centroid is None:
            return

        entry_line = (self.lines["entry"]["x1"], self.lines["entry"]["y1"]), \
                     (self.lines["entry"]["x2"], self.lines["entry"]["y2"])
        exit_line = (self.lines["exit"]["x1"], self.lines["exit"]["y1"]), \
                    (self.lines["exit"]["x2"], self.lines["exit"]["y2"])

        if self.direction == "horizontal":
            line_y_entry = entry_line[0][1]
            line_y_exit = exit_line[0][1]
            if prev_centroid[1] < line_y_entry <= current_centroid[1]:
                self.vehicle_count += 1
            elif prev_centroid[1] > line_y_exit >= current_centroid[1]:
                self.vehicle_count = max(0, self.vehicle_count - 1)

    def _draw_lines(self, frame):
        color_entry = (0, 255, 0)
        color_exit = (0, 0, 255)
        cv2.line(frame, (self.lines["entry"]["x1"], self.lines["entry"]["y1"]),
                 (self.lines["entry"]["x2"], self.lines["entry"]["y2"]), color_entry, 2)
        cv2.line(frame, (self.lines["exit"]["x1"], self.lines["exit"]["y1"]),
                 (self.lines["exit"]["x2"], self.lines["exit"]["y2"]), color_exit, 2)

    def get_frame(self):
        with self.lock:
            return self.last_frame

    def get_status(self):
        with self.lock:
            return {
                "camera_id": self.camera_id,
                "vehicle_count": self.vehicle_count,
                "free_spots": self.capacity - self.vehicle_count,
                "capacity": self.capacity
            }