# docker/worker-gpu.Dockerfile
# Base image provides ffmpeg with NVENC (change tag as required)
# Note: use a prebuilt ffmpeg with nvenc support. Example: jrottenberg/ffmpeg:4.4-nvidia
FROM jrottenberg/ffmpeg:4.4-nvidia

# install python & extras
RUN apt-get update && apt-get install -y python3 python3-pip git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# copy project files
COPY . /app

# install python deps (adjust as per your requirements)
RUN pip3 install --no-cache-dir -r requirements.txt

# environment variables to help processes use GPU
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,video,utility

# default command: start celery worker for GPU tasks
CMD ["bash", "-lc", "celery -A celery_app.celery worker --loglevel=info --concurrency=1 -Q gpu"]
