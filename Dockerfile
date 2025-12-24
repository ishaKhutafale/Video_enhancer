# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies (FFmpeg, build tools, Vulkan for Real-ESRGAN)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    unzip \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p input output frames upscaled

# Make Real-ESRGAN executable
RUN chmod +x bin/realesrgan-ncnn-vulkan || chmod +x bin/realesrgan-ncnn-vulkan.exe || true

# Expose port (Cloud Run uses PORT environment variable)
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 0 app:app
