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
    "total": 1
}

# Background enhancement thread
def run_enhance(video_path):
    def update(curr, total):
        progress["current"] = curr
        progress["total"] = total

    enhance_video(video_path, update)

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

    # Run enhancement in background
    threading.Thread(
        target=run_enhance,
        args=(input_path,),
        daemon=True
    ).start()

    return jsonify({"status": "started"})

@app.route("/progress")
def get_progress():
    return jsonify(progress)

# Serve output video properly
@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(
        OUTPUT_FOLDER, filename, mimetype="video/mp4"
    )

# Run app
if __name__ == "__main__":
    app.run(debug=True)

