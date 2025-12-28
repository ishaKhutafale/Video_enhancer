import os
import subprocess
import shutil
import platform

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
TMP_FRAMES = os.path.join(PROJECT_ROOT, "frames")
FOLDER_UPSCALE = os.path.join(PROJECT_ROOT, "upscaled")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

UPSCALE_FACTOR = 2
GPU_MODE = "0"  # 0 = CPU only
TILE_SIZE = "256"

# Check for Real-ESRGAN executable - Platform-aware detection
IS_WINDOWS = platform.system() == "Windows"
BIN_RR_EXE = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan.exe")
BIN_RR_NO_EXT = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan")

# Prioritize based on platform
if IS_WINDOWS:
    # On Windows, prefer .exe
    if os.path.exists(BIN_RR_EXE):
        BIN_RR = BIN_RR_EXE
    elif os.path.exists(BIN_RR_NO_EXT):
        BIN_RR = BIN_RR_NO_EXT
    else:
        raise FileNotFoundError(
            "Real-ESRGAN executable not found!\n"
            "Download from: https://github.com/xinntao/Real-ESRGAN/releases\n"
            "1. Download 'realesrgan-ncnn-vulkan-20220424-windows.zip'\n"
            "2. Extract 'realesrgan-ncnn-vulkan.exe' to the 'bin' folder\n"
            "3. Also extract the 'models' folder to 'bin/models'"
        )
else:
    # On Linux/Mac, use non-.exe version
    if os.path.exists(BIN_RR_NO_EXT):
        BIN_RR = BIN_RR_NO_EXT
    else:
        raise FileNotFoundError(
            "Real-ESRGAN executable not found!\n"
            "For Linux, it should be at: bin/realesrgan-ncnn-vulkan\n"
            "The binary is included in the Docker image."
        )

# Check for FFmpeg - Platform-aware
if IS_WINDOWS:
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
else:
    # On Linux/Mac, FFmpeg should be in PATH or system installed
    if shutil.which("ffmpeg"):
        FFMPEG_CMD = "ffmpeg"
    else:
        raise FileNotFoundError(
            "FFmpeg not found! It should be installed in the Docker image."
        )


def upscale_frame_data(args):
    """Upscale a single frame - wrapper for sequential processing"""
    frame_num, progress_callback, current, total = args
    infile = os.path.join(TMP_FRAMES, f"{frame_num:06d}.jpg")
    outfile = os.path.join(FOLDER_UPSCALE, f"{frame_num:06d}.jpg")
    
    print(f"[Frame {current}/{total}] Processing frame {frame_num:06d}.jpg", flush=True)
    
    try:
        result = subprocess.run([
            BIN_RR,
            "-i", infile,
            "-o", outfile,
            "-s", str(UPSCALE_FACTOR),
            "-g", GPU_MODE,
            "-t", TILE_SIZE
        ], capture_output=True, text=True, check=True, timeout=60)
        
        print(f"[Frame {current}/{total}] Completed frame {frame_num:06d}.jpg", flush=True)
        
        if progress_callback:
            progress_callback(current, total)
        return True
    except subprocess.TimeoutExpired as e:
        print(f"[Frame {current}/{total}] TIMEOUT on frame {frame_num:06d}.jpg after 60s", flush=True)
        return False
    except subprocess.CalledProcessError as e:
        print(f"[Frame {current}/{total}] ERROR on frame {frame_num:06d}.jpg", flush=True)
        print(f"  Command: {' '.join(e.cmd)}", flush=True)
        print(f"  Return code: {e.returncode}", flush=True)
        print(f"  Stderr: {e.stderr}", flush=True)
        print(f"  Stdout: {e.stdout}", flush=True)
        return False
    except Exception as e:
        print(f"[Frame {current}/{total}] EXCEPTION on frame {frame_num:06d}.jpg: {str(e)}", flush=True)
        return False


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
    
    print(f"="*60, flush=True)
    print(f"STARTING REAL-ESRGAN ENHANCEMENT", flush=True)
    print(f"Total frames: {total}", flush=True)
    print(f"Upscale factor: {UPSCALE_FACTOR}x", flush=True)
    print(f"GPU mode: {GPU_MODE} (0=CPU)", flush=True)
    print(f"Tile size: {TILE_SIZE}", flush=True)
    print(f"Binary: {BIN_RR}", flush=True)
    print(f"="*60, flush=True)
    
    # Upscale frames sequentially (Cloud Run compatible)
    # Frame numbers start at 1, not 0
    success_count = 0
    for idx in range(total):
        frame_num = idx + 1  # Frames are numbered 000001, 000002, etc.
        result = upscale_frame_data((frame_num, progress_callback, idx + 1, total))
        if result:
            success_count += 1
    
    print(f"="*60, flush=True)
    print(f"ENHANCEMENT COMPLETE: {success_count}/{total} frames successful", flush=True)
    print(f"="*60, flush=True)
    
    if success_count == 0:
        raise RuntimeError(f"All {total} frames failed to upscale! Check logs above for errors.")
    elif success_count < total:
        print(f"WARNING: Only {success_count}/{total} frames were successfully upscaled", flush=True)

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

