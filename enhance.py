import os
import subprocess
from multiprocessing import Pool
from agent import EnhancementAgent

# ------------------ PATH SETUP ------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
TMP_FRAMES = os.path.join(PROJECT_ROOT, "frames")
FOLDER_UPSCALE = os.path.join(PROJECT_ROOT, "upscaled")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

GPU_MODE = "0"  # CPU-only flag

# ------------------ AUTO THREAD CONFIG ------------------
CPU_CORES = os.cpu_count() or 2
FFMPEG_THREADS = max(1, int(CPU_CORES * 0.3))

print(f"[SYSTEM] CPU cores: {CPU_CORES} | FFmpeg threads: {FFMPEG_THREADS}")

# ------------------ EXECUTABLES ------------------
BIN_RR = os.path.join(BIN_DIR, "realesrgan-ncnn-vulkan")
FFMPEG_CMD = "ffmpeg"


# ------------------ FRAME PIPELINE ------------------
def upscale_frame(args):
    i, upscale_factor, tile_size, mode = args

    src = os.path.join(TMP_FRAMES, f"{i:06d}.jpg")
    ai = os.path.join(FOLDER_UPSCALE, f"{i:06d}_ai.jpg")
    final = os.path.join(FOLDER_UPSCALE, f"{i:06d}.jpg")

    # ---- STEP 1: AI UPSCALE ----
    subprocess.run(
        [
            BIN_RR,
            "-i", src,
            "-o", ai,
            "-g", GPU_MODE,
            "-s", str(upscale_factor),
            "-t", str(tile_size),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if not os.path.exists(ai):
        return 0

    # ---- STEP 2: CONDITIONAL FILTER ----
    if mode == "human":
        vf = "unsharp=3:3:0.25,noise=alls=4:allf=t+u"
    else:
        vf = None

    if vf:
        subprocess.run(
            [
                FFMPEG_CMD,
                "-y",
                "-threads", str(FFMPEG_THREADS),
                "-i", ai,
                "-vf", vf,
                final
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        os.rename(ai, final)

    if os.path.exists(ai):
        os.remove(ai)

    return 1


# ------------------ MAIN PIPELINE ------------------
def enhance_video(input_video, progress_callback=None):
    print("\n========== VIDEO ENHANCEMENT START ==========\n")

    agent = EnhancementAgent(input_video)
    decisions = agent.make_decisions()

    os.makedirs(TMP_FRAMES, exist_ok=True)
    os.makedirs(FOLDER_UPSCALE, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Clear folders
    for folder in [TMP_FRAMES, FOLDER_UPSCALE]:
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))

    enhanced_no_audio = os.path.join(OUTPUT_DIR, "enhanced_no_audio.mp4")
    final_output = os.path.join(OUTPUT_DIR, "enhanced_output.mp4")

    # ---- EXTRACT FRAMES ----
    subprocess.run(
        [
            FFMPEG_CMD,
            "-y",
            "-threads", str(FFMPEG_THREADS),
            "-i", input_video,
            "-vf", "fps=15",
            os.path.join(TMP_FRAMES, "%06d.jpg")
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    frames = sorted(os.listdir(TMP_FRAMES))
    total = len(frames)
    print(f"[SYSTEM] Frames extracted: {total}")

    # ---- DETECT VIDEO TYPE ----
    sample_frame = os.path.join(TMP_FRAMES, frames[0])
    decisions["mode"] = agent.detect_video_type(sample_frame)

    print(f"[SYSTEM] Mode selected: {decisions['mode'].upper()}")
    print("\n[PROCESS] Upscaling started...\n")

    # ---- PROCESS FRAMES ----
    tasks = [
        (i + 1, decisions["upscale_factor"], decisions["tile_size"], decisions["mode"])
        for i in range(total)
    ]

    done = 0
    with Pool(decisions["workers"]) as pool:
        for _ in pool.imap_unordered(upscale_frame, tasks):
            done += 1

            # Horizontal progress update
            print(f"\r[PROGRESS] {done}/{total} frames done", end="")

            if progress_callback:
                progress_callback(done, total)

    print("\n\n[PROCESS] Rebuilding video...")

    # ---- REBUILD VIDEO ----
    subprocess.run(
        [
            FFMPEG_CMD,
            "-y",
            "-threads", str(FFMPEG_THREADS),
            "-framerate", "15",
            "-i", os.path.join(FOLDER_UPSCALE, "%06d.jpg"),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            enhanced_no_audio
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # ---- MERGE AUDIO ----
    subprocess.run(
        [
            FFMPEG_CMD,
            "-y",
            "-threads", str(FFMPEG_THREADS),
            "-i", enhanced_no_audio,
            "-i", input_video,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-shortest",
            final_output
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("\n========== DONE ==========")
    print(f"[SYSTEM] Final video saved: {final_output}")

    return final_output

