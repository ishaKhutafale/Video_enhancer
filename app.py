from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    make_response
)

import os
import threading
import multiprocessing
import time
import logging

from enhance import enhance_video

# REQUIRED for multiprocessing on Windows
multiprocessing.freeze_support()

app = Flask(__name__)

# --------------------------------------------------------
# Hide ONLY /progress request spam
# Keeps startup links + real errors visible
# --------------------------------------------------------

class ProgressFilter(logging.Filter):
    def filter(self, record):
        return "/progress" not in record.getMessage()

werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.addFilter(ProgressFilter())

# ---------------- PATHS ----------------
UPLOAD_FOLDER = "input"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ---------------- PROGRESS STATE ----------------
progress = {
    "current": 0,
    "total": 1,
    "status": "idle",   # idle | processing | completed | error
    "message": ""
}

# ---------------- BACKGROUND ENHANCEMENT ----------------

def run_enhance(video_path):

    def update(curr, total):
        progress["current"] = curr
        progress["total"] = total
        progress["status"] = "processing"
        progress["message"] = f"Upscaling frame {curr}/{total}"

    try:
        progress["status"] = "processing"
        progress["message"] = "Agent analyzing video and deciding parameters..."

        # Remove old output if exists
        output_path = os.path.join(OUTPUT_FOLDER, "enhanced_output.mp4")

        if os.path.exists(output_path):
            os.remove(output_path)

        # Run enhancement
        enhance_video(video_path, update)

        progress["status"] = "completed"
        progress["message"] = "Enhancement completed successfully!"

    except Exception as e:
        progress["status"] = "error"
        progress["message"] = f"Error: {str(e)}"


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- UPLOAD VIDEO ----------------

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["video"]

    # Unique filename to avoid overwrite
    filename = f"input_{int(time.time())}.mp4"
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)

    # Reset progress
    progress["current"] = 0
    progress["total"] = 1
    progress["status"] = "idle"
    progress["message"] = "Upload complete. Starting enhancement..."

    # Start enhancement in background thread
    threading.Thread(
        target=run_enhance,
        args=(input_path,),
        daemon=True
    ).start()

    return jsonify({
        "status": "started",
        "input_video": filename
    })


# ---------------- PROGRESS API ----------------

@app.route("/progress")
def get_progress():
    return jsonify(progress)


# ---------------- SERVE OUTPUT VIDEO ----------------

@app.route("/output/<path:filename>")
def serve_output(filename):
    response = make_response(
        send_from_directory(OUTPUT_FOLDER, filename)
    )

    # FIXED HEADERS FOR VIDEO PLAYBACK
    response.headers["Content-Type"] = "video/mp4"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Disposition"] = "inline"

    return response


# ---------------- SERVE INPUT VIDEO ----------------

@app.route("/input/<path:filename>")
def serve_input(filename):
    response = make_response(
        send_from_directory(UPLOAD_FOLDER, filename)
    )

    response.headers["Content-Type"] = "video/mp4"
    response.headers["Cache-Control"] = "no-store"

    return response


# ---------------- CHECK OUTPUT READY ----------------

@app.route("/check_output")
def check_output():
    output_path = os.path.join(OUTPUT_FOLDER, "enhanced_output.mp4")

    # File not created yet
    if not os.path.exists(output_path):
        return jsonify({
            "exists": False,
            "ready": False,
            "filename": None
        })

    # File exists but may still be incomplete
    try:
        size = os.path.getsize(output_path)
    except OSError:
        size = 0

    # Must be at least 50KB to be considered valid MP4
    if size < 50000:
        return jsonify({
            "exists": True,
            "ready": False,
            "filename": None
        })

    return jsonify({
        "exists": True,
        "ready": True,
        "filename": "enhanced_output.mp4"
    })


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )

