# Video Enhancer

CPU-safe enhancement pipeline to extract video frames, deblur + upscale with RealESRGAN, and rebuild video (with audio if exists).  

## Prerequisites

- Python 3.7+ (or compatible)  
- `ffmpeg` and `ffprobe` installed and available in PATH (for audio/video merging)  
- `git`  

## How to get started

### Clone this repository

```bash
git clone https://github.com/ishaKhutafale/Video_enhancer.git
cd Video_enhancer

```
# Setup & Run (Linux / macOS)
```bash
# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the enhancer
python app.py
```

# Setup & Run (Windows)
```bash
# 1. Create a virtual environment
py -m venv venv

# 2. Activate the virtual environment
venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the enhancer
python app.py

```

# Usage

Place the input video at input/input.mp4.
The script will extract frames, apply upscale with RealESRGAN, and assemble a new video.
Final output will be created at output/enhanced_output.mp4.

