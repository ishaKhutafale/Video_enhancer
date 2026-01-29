import subprocess
from multiprocessing import cpu_count
import cv2
import numpy as np
import os
import psutil


class EnhancementAgent:
    def __init__(self, input_video):
        self.input_video = input_video
        self.cores = cpu_count()
        self.available_ram_gb = psutil.virtual_memory().available / 1e9

    def analyze_video(self):
        """Extract width and height using ffprobe"""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "default=noprint_wrappers=1",
            self.input_video
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        info = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=")
                info[k] = int(v)

        width = info.get("width", 640)
        height = info.get("height", 360)

        print(f"[AGENT] Resolution: {width}x{height}")
        return width, height

    def decide_upscale_factor(self, width):
        if width <= 640:
            decision = 3
        elif width <= 1280:
            decision = 2
        else:
            decision = 1

        print(f"[AGENT] Upscale factor: x{decision}")
        return decision

    def decide_tile_size(self, width, height):
        max_dim = max(width, height)

        if max_dim <= 1080:
            tile = 128
        elif max_dim <= 1440:
            tile = 192
        else:
            tile = 256

        if self.available_ram_gb < 4 and tile > 128:
            tile = 128

        print(f"[AGENT] Tile size: {tile}")
        return str(tile)

    def decide_cpu_workers(self):
        print("[AGENT] Workers: 1 (CPU-safe mode)")
        return 1

    def detect_video_type(self, sample_frame_path):
        """Detect anime vs human using heuristic"""

        if not os.path.exists(sample_frame_path):
            return "human"

        img = cv2.imread(sample_frame_path)
        if img is None:
            return "human"

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Face detection
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            return "human"

        # Saturation + Edge density
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1])

        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1]) * 100

        if saturation > 80 and edge_density < 8:
            return "anime"
        return "human"

    def make_decisions(self):
        width, height = self.analyze_video()

        decisions = {
            "upscale_factor": self.decide_upscale_factor(width),
            "tile_size": self.decide_tile_size(width, height),
            "workers": self.decide_cpu_workers(),
            "mode": "human"
        }

        return decisions

