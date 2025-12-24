from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
from enhance import enhance_video

app = Flask(__name__)

# Paths
UPLOAD_FOLDER = "input"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Progress state
progress = {
    "current": 0,
    "total": 1,
    "status": "idle",  # idle, processing, completed, error
    "message": ""
}

# Background enhancement thread
def run_enhance(video_path):
    def update(curr, total):
        progress["current"] = curr
        progress["total"] = total
        progress["status"] = "processing"
        progress["message"] = f"Processing frame {curr}/{total}"
    
    try:
        progress["status"] = "processing"
        progress["message"] = "Starting enhancement..."
        enhance_video(video_path, update)
        progress["status"] = "completed"
        progress["message"] = "Enhancement completed successfully!"
    except Exception as e:
        progress["status"] = "error"
        progress["message"] = f"Error: {str(e)}"

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["video"]
    input_path = os.path.join(UPLOAD_FOLDER, "input.mp4")
    file.save(input_path)

    # Reset progress
    progress["current"] = 0
    progress["total"] = 1
    progress["status"] = "idle"
    progress["message"] = ""

    # Run enhancement in background
    threading.Thread(
        target=run_enhance,
        args=(input_path,),
        daemon=True
    ).start()

    return jsonify({"status": "started", "input_video": "input.mp4"})

@app.route("/progress")
def get_progress():
    return jsonify(progress)

# Serve output video properly
@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(
        OUTPUT_FOLDER, filename, mimetype="video/mp4"
    )

# Serve input video for preview
@app.route("/input/<path:filename>")
def serve_input(filename):
    return send_from_directory(
        UPLOAD_FOLDER, filename, mimetype="video/mp4"
    )

# Check if output video exists
@app.route("/check_output")
def check_output():
    output_path = os.path.join(OUTPUT_FOLDER, "enhanced_output.mp4")
    exists = os.path.exists(output_path)
    size = os.path.getsize(output_path) if exists else 0
    return jsonify({
        "exists": exists,
        "ready": exists and size > 0,
        "filename": "enhanced_output.mp4" if exists else None
    })

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

