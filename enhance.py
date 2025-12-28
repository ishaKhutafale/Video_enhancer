import os
import subprocess
import shutil
import platform
import cv2
import sys
import numpy as np
from pathlib import Path

# Try to import Real-ESRGAN
try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer
    USE_REALESRGAN = True
    print("Real-ESRGAN Python library loaded successfully", flush=True)
except ImportError as e:
    USE_REALESRGAN = False
    print(f"Real-ESRGAN not available, using OpenCV: {e}", flush=True)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
TMP_FRAMES = os.path.join(PROJECT_ROOT, "frames")
FOLDER_UPSCALE = os.path.join(PROJECT_ROOT, "upscaled")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

UPSCALE_FACTOR = 2

# Initialize Real-ESRGAN upsampler (global, created once)
UPSAMPLER = None

def init_realesrgan():
    """Initialize Real-ESRGAN model once"""
    global UPSAMPLER
    if UPSAMPLER is not None:
        return UPSAMPLER
    
    if not USE_REALESRGAN:
        return None
    
    try:
        print("Initializing Real-ESRGAN model...", flush=True)
        
        # Use RealESRGAN_x2plus model (good balance of speed/quality)
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        
        # Model path
        model_path = os.path.join(BIN_DIR, 'models', 'RealESRGAN_x2plus.pth')
        
        # Download model if not exists
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}, will use default", flush=True)
            model_path = None  # Let RealESRGANer download it
        
        UPSAMPLER = RealESRGANer(
            scale=2,
            model_path=model_path,
            model=model,
            tile=256,
            tile_pad=10,
            pre_pad=0,
            half=False,  # Use FP32 for CPU
            device='cpu'
        )
        
        print("Real-ESRGAN initialized successfully on CPU", flush=True)
        return UPSAMPLER
    except Exception as e:
        print(f"Failed to initialize Real-ESRGAN: {e}", flush=True)
        print("Falling back to OpenCV", flush=True)
        return None

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
        # Test if binary is executable
        if not os.access(BIN_RR, os.X_OK):
            print(f"WARNING: {BIN_RR} is not executable! Attempting to fix...", flush=True)
            try:
                os.chmod(BIN_RR, 0o755)
                print(f"Fixed permissions on {BIN_RR}", flush=True)
            except Exception as e:
                print(f"ERROR: Could not fix permissions: {e}", flush=True)
        
        # Test binary with --help
        print(f"Testing Real-ESRGAN binary: {BIN_RR}", flush=True)
        try:
            test_result = subprocess.run([BIN_RR], capture_output=True, text=True, timeout=5)
            print(f"Binary test stdout: {test_result.stdout[:200]}", flush=True)
            print(f"Binary test stderr: {test_result.stderr[:200]}", flush=True)
            print(f"Binary test return code: {test_result.returncode}", flush=True)
        except Exception as e:
            print(f"WARNING: Binary test failed: {e}", flush=True)
            print(f"This may indicate Vulkan/GPU issues - processing will be slow or fail", flush=True)
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
    """Upscale a single frame using Real-ESRGAN or OpenCV fallback"""
    frame_num, progress_callback, current, total, upsampler = args
    infile = os.path.join(TMP_FRAMES, f"{frame_num:06d}.jpg")
    outfile = os.path.join(FOLDER_UPSCALE, f"{frame_num:06d}.jpg")
    
    if current % 10 == 1 or current == total:
        print(f"[Frame {current}/{total}] Processing frame {frame_num:06d}.jpg", flush=True)
    
    try:
        # Read image
        img = cv2.imread(infile)
        if img is None:
            print(f"[Frame {current}/{total}] ERROR: Could not read {infile}", flush=True)
            return False
        
        # Try Real-ESRGAN first, fallback to OpenCV
        if upsampler is not None:
            try:
                # Real-ESRGAN expects RGB
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                output, _ = upsampler.enhance(img_rgb, outscale=2)
                # Convert back to BGR for saving
                upscaled = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)
            except Exception as e:
                if current == 1:
                    print(f"Real-ESRGAN failed, using OpenCV: {e}", flush=True)
                # Fallback to OpenCV
                height, width = img.shape[:2]
                upscaled = cv2.resize(img, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        else:
            # Use OpenCV
            height, width = img.shape[:2]
            upscaled = cv2.resize(img, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Save upscaled image
        cv2.imwrite(outfile, upscaled, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if progress_callback:
            progress_callback(current, total)
        return True
    except Exception as e:
        print(f"[Frame {current}/{total}] EXCEPTION: {str(e)}", flush=True)
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
    
    # Initialize Real-ESRGAN
    upsampler = init_realesrgan()
    method = "Real-ESRGAN (CPU)" if upsampler else "OpenCV INTER_CUBIC"
    
    print(f"="*60, flush=True)
    print(f"STARTING VIDEO ENHANCEMENT", flush=True)
    print(f"Total frames: {total}", flush=True)
    print(f"Upscale factor: {UPSCALE_FACTOR}x", flush=True)
    print(f"Method: {method}", flush=True)
    if upsampler:
        print(f"Note: CPU processing is slow (~30-60s per frame)", flush=True)
    print(f"="*60, flush=True)
    
    # Upscale frames sequentially (Cloud Run compatible)
    # Frame numbers start at 1, not 0
    success_count = 0
    for idx in range(total):
        frame_num = idx + 1  # Frames are numbered 000001, 000002, etc.
        result = upscale_frame_data((frame_num, progress_callback, idx + 1, total, upsampler))
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

