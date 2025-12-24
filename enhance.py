import os
import subprocess
from multiprocessing import Pool, cpu_count
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
TMP_FRAMES = os.path.join(PROJECT_ROOT, "frames")
FOLDER_UPSCALE = os.path.join(PROJECT_ROOT, "upscaled")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

UPSCALE_FACTOR = 2
GPU_MODE = "0"  # 0 = CPU only
TILE_SIZE = "256"

# Check for Real-ESRGAN executable (Windows needs .exe)
BIN_RR_EXE = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan.exe")
BIN_RR_NO_EXT = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan")

if os.path.exists(BIN_RR_EXE):
    BIN_RR = BIN_RR_EXE
elif os.path.exists(BIN_RR_NO_EXT):
    # Check if it's actually a Windows executable
    try:
        result = subprocess.run([BIN_RR_NO_EXT, "--help"], 
                              capture_output=True, timeout=2)
        BIN_RR = BIN_RR_NO_EXT
    except (OSError, subprocess.TimeoutExpired):
        raise FileNotFoundError(
            "Real-ESRGAN Windows executable not found!\n"
            "Download from: https://github.com/xinntao/Real-ESRGAN/releases\n"
            "1. Download 'realesrgan-ncnn-vulkan-20220424-windows.zip'\n"
            "2. Extract 'realesrgan-ncnn-vulkan.exe' to the 'bin' folder\n"
            "3. Also extract the 'models' folder to 'bin/models'"
        )
else:
    raise FileNotFoundError(
        "Real-ESRGAN executable not found in bin folder!\n"
        "Download from: https://github.com/xinntao/Real-ESRGAN/releases\n"
        "1. Download 'realesrgan-ncnn-vulkan-20220424-windows.zip'\n"
        "2. Extract 'realesrgan-ncnn-vulkan.exe' to the 'bin' folder\n"
        "3. Also extract the 'models' folder to 'bin/models'"
    )

# Check for FFmpeg - first in bin folder, then in PATH, then common install locations
FFMPEG_LOCAL = os.path.join(BIN_DIR, "ffmpeg.exe")
FFMPEG_CHOCOLATEY = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
FFMPEG_CHOCO_LIB = r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin\ffmpeg.exe"

if os.path.exists(FFMPEG_LOCAL):
    FFMPEG_CMD = FFMPEG_LOCAL
elif os.path.exists(FFMPEG_CHOCOLATEY):
    FFMPEG_CMD = FFMPEG_CHOCOLATEY
elif os.path.exists(FFMPEG_CHOCO_LIB):
    FFMPEG_CMD = FFMPEG_CHOCO_LIB
elif shutil.which("ffmpeg"):
    FFMPEG_CMD = "ffmpeg"
else:
    raise FileNotFoundError(
        "FFmpeg not found! Please install FFmpeg:\n"
        "1. Via Chocolatey: choco install ffmpeg\n"
        "2. Or download from https://www.gyan.dev/ffmpeg/builds/ and add to PATH\n"
        "3. Or place ffmpeg.exe in the 'bin' folder"
    )


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
        FFMPEG_CMD, "-y", "-i", input_video,
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
        FFMPEG_CMD, "-y", "-framerate", "24",
        "-i", os.path.join(FOLDER_UPSCALE, "%06d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        enhanced_no_audio
    ], check=True)

 
    # Merge original audio back
    subprocess.run([
        FFMPEG_CMD, "-y",
        "-i", enhanced_no_audio,
        "-i", input_video,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        final_output
    ], check=True)

