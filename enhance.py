import os
import subprocess
from multiprocessing import Pool, cpu_count

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
TMP_FRAMES = os.path.join(PROJECT_ROOT, "frames")
FOLDER_UPSCALE = os.path.join(PROJECT_ROOT, "upscaled")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

UPSCALE_FACTOR = 2
GPU_MODE = "0"  # 0 = CPU only
TILE_SIZE = "256"

BIN_RR = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan")


def upscale_frame(i):
    infile = os.path.join(TMP_FRAMES, f"{i:06d}.jpg")
    outfile = os.path.join(FOLDER_UPSCALE, f"{i:06d}.jpg")
    subprocess.run([
        BIN_RR,
        "-i", infile,
        "-o", outfile,
        "-s", str(UPSCALE_FACTOR),
        "-g", GPU_MODE,
        "-t", TILE_SIZE
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 1


def enhance_video(input_video, progress_callback=None):
    os.makedirs(TMP_FRAMES, exist_ok=True)
    os.makedirs(FOLDER_UPSCALE, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Clean old files
    for folder in [TMP_FRAMES, FOLDER_UPSCALE]:
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))

    enhanced_no_audio = os.path.join(OUTPUT_DIR, "enhanced_no_audio.mp4")
    final_output = os.path.join(OUTPUT_DIR, "enhanced_output.mp4")

    # Extract frames
    subprocess.run([
        "ffmpeg", "-y", "-i", input_video,
        os.path.join(TMP_FRAMES, "%06d.jpg")
    ], check=True)

    frames = sorted(f for f in os.listdir(TMP_FRAMES) if f.endswith(".jpg"))
    total = len(frames)
    done = 0

    # Upscale frames (CPU-safe)
    with Pool(max(1, cpu_count() // 2)) as pool:
        for _ in pool.imap_unordered(upscale_frame, range(total)):
            done += 1
            if progress_callback:
                progress_callback(done, total)

    # Rebuild video (NO audio)
    # Browser compatible format
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "24",
        "-i", os.path.join(FOLDER_UPSCALE, "%06d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        enhanced_no_audio
    ], check=True)

 
    # Merge original audio back
    subprocess.run([
        "ffmpeg", "-y",
        "-i", enhanced_no_audio,
        "-i", input_video,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        final_output
    ], check=True)

