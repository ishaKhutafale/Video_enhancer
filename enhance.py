#!/usr/bin/env python3
"""
CPU-safe enhancement pipeline (FASTER VERSION)
 - Extract frames
 - Deblur + upscale (RealESRGAN only)
Designed to run on CPU only (no GPU)
"""

import os
import cv2
import subprocess
from tqdm import tqdm
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
INPUT_VIDEO = os.path.join(PROJECT_ROOT, "input", "input.mp4")

TMP_FRAMES = os.path.join(PROJECT_ROOT, "frames")
FOLDER_UPSCALE = os.path.join(PROJECT_ROOT, "upscaled")
OUTPUT_VIDEO = os.path.join(PROJECT_ROOT, "output", "enhanced_output.mp4")

UPSCALE_FACTOR = 2
GPU_MODE = "0"        # CPU only
TILE_SIZE = "128"     # small tile = low heat

BIN_RR = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan")

for d in [TMP_FRAMES, FOLDER_UPSCALE, os.path.join(PROJECT_ROOT, "output")]:
    os.makedirs(d, exist_ok=True)

# ----- Extract frames -----
cap = cv2.VideoCapture(INPUT_VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS)
count = 0
while True:
    ret, frame = cap.read()
    if not ret: break
    cv2.imwrite(os.path.join(TMP_FRAMES, f"{count:06d}.png"), frame)
    count += 1
cap.release()
print(f"Frames extracted: {count}")

def run_cmd(cmd):
    subprocess.run(cmd, check=True)

# ----- Deblur + Upscale (only RealESRGAN) -----
print("Upscaling with RealESRGAN...")
for i in tqdm(range(count)):
    infile = os.path.join(TMP_FRAMES, f"{i:06d}.png")
    outfile = os.path.join(FOLDER_UPSCALE, f"{i:06d}.png")
    cmd = [
        BIN_RR, "-i", infile, "-o", outfile,
        "-s", str(UPSCALE_FACTOR),
        "-g", GPU_MODE, "-t", TILE_SIZE
    ]
    run_cmd(cmd)

# ----- Rebuild video without audio (current code) -----
first = os.path.join(FOLDER_UPSCALE, "000000.png")
h, w = cv2.imread(first).shape[:2]
temp_video = os.path.join(PROJECT_ROOT, "output", "noaudio.mp4")
video = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
for i in tqdm(range(count)):
    video.write(cv2.imread(os.path.join(FOLDER_UPSCALE, f"{i:06d}.png")))
video.release()

# ----- Merge original audio safely (only if audio exists) -----
final_output = OUTPUT_VIDEO  # already defined

# Check if original video has audio using ffprobe
audio_check = subprocess.run(
    ["ffprobe", "-i", INPUT_VIDEO, "-show_streams", "-select_streams", "a", "-loglevel", "error"]
)

if audio_check.returncode == 0:
    # Audio exists, merge it
    cmd_audio = [
        "ffmpeg",
        "-y",
        "-i", temp_video,           # upscaled video
        "-i", INPUT_VIDEO,          # original video with audio
        "-c:v", "copy",             # copy video without re-encoding
        "-c:a", "aac",              # encode audio as AAC
        "-map", "0:v:0",            # take video from first input
        "-map", "1:a:0",            # take audio from second input
        final_output
    ]
    run_cmd(cmd_audio)
    os.remove(temp_video)
else:
    # No audio found, just rename temp video
    shutil.move(temp_video, final_output)

print("Done! Final video saved as:", final_output)

