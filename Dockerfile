# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies (FFmpeg, build tools, Vulkan for Real-ESRGAN)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    unzip \
    libvulkan1 \
    file \
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

# Download correct Real-ESRGAN binary for Linux
RUN echo "Downloading Real-ESRGAN for Linux..." && \
    wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip && \
    unzip -q realesrgan-ncnn-vulkan-20220424-ubuntu.zip && \
    mv realesrgan-ncnn-vulkan-20220424-ubuntu/realesrgan-ncnn-vulkan bin/realesrgan-ncnn-vulkan && \
    chmod +x bin/realesrgan-ncnn-vulkan && \
    rm -rf realesrgan-ncnn-vulkan-20220424-ubuntu* && \
    echo "Binary downloaded and installed" && \
    file bin/realesrgan-ncnn-vulkan

# Expose port (Cloud Run uses PORT environment variable)
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 0 app:app
