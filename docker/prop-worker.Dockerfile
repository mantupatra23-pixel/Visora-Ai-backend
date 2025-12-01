# docker/prop-worker.Dockerfile
FROM nvidia/cuda:11.7.0-cudnn8-devel-ubuntu20.04

RUN apt-get update && apt-get install -y python3 python3-pip wget ca-certificates libgl1 && rm -rf /var/lib/apt/lists/*

ARG BLENDER_VERSION=3.5.1
RUN wget https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz -O /tmp/blender.tar.xz \
  && tar -xJf /tmp/blender.tar.xz -C /opt/ && rm /tmp/blender.tar.xz
ENV PATH="/opt/blender-${BLENDER_VERSION}-linux-x64:${PATH}"
ENV BLENDER_BIN="/opt/blender-${BLENDER_VERSION}-linux-x64/blender"

WORKDIR /app
COPY . /app
RUN pip3 install --no-cache-dir celery redis

ENV CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://redis:6379/0}
CMD ["bash","-lc","celery -A tasks.prop_tasks worker --loglevel=info -Q props"]
