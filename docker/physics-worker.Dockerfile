# docker/physics-worker.Dockerfile
FROM nvidia/cuda:11.7.0-cudnn8-devel-ubuntu20.04

# install ffmpeg, blender dependencies & python
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-pip git wget curl ca-certificates libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Blender (example using apt snap is unreliable). Download official tarball:
ARG BLENDER_VERSION=3.5.1
RUN wget https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz -O /tmp/blender.tar.xz \
    && tar -xJf /tmp/blender.tar.xz -C /opt/ \
    && rm /tmp/blender.tar.xz
ENV PATH="/opt/blender-${BLENDER_VERSION}-linux-x64:${PATH}"
ENV BLENDER_BIN="/opt/blender-${BLENDER_VERSION}-linux-x64/blender"

WORKDIR /app
COPY . /app
RUN pip3 install --no-cache-dir -r requirements.txt

ENV CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://redis:6379/0}
ENV BLENDER_BIN=${BLENDER_BIN:-/opt/blender-${BLENDER_VERSION}-linux-x64/blender}

CMD ["bash","-lc","celery -A tasks.physics_tasks worker --loglevel=info -Q physics"]
