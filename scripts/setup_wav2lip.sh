#!/usr/bin/env bash
set -e
ROOT="$(pwd)"
REPO_DIR="${ROOT}/wav2lip_repo"

echo "1) Cloning Wav2Lip (official) into ${REPO_DIR}..."
if [ ! -d "$REPO_DIR" ]; then
  git clone https://github.com/Rudrabha/Wav2Lip.git "$REPO_DIR"
else
  echo "Repo exists, pulling latest..."
  cd "$REPO_DIR" && git fetch --all && git pull || true
  cd "$ROOT"
fi

echo "2) Ensure checkpoints directory..."
mkdir -p "${REPO_DIR}/checkpoints"

cd "${REPO_DIR}/checkpoints"

# download models (safe public mirrors)
echo "Downloading Wav2Lip.pth..."
if [ ! -f Wav2Lip.pth ]; then
  wget -c https://huggingface.co/spaces/akhaliq/Wav2Lip/resolve/main/Wav2Lip.pth
fi

echo "Downloading Wav2Lip_gan.pth (optional)..."
if [ ! -f Wav2Lip_gan.pth ]; then
  wget -c https://huggingface.co/spaces/akhaliq/Wav2Lip/resolve/main/Wav2Lip_gan.pth || true
fi

echo "Downloading s3fd.pth..."
if [ ! -f s3fd.pth ]; then
  wget -c https://huggingface.co/spaces/akhaliq/Wav2Lip/resolve/main/face_detection/detection/s3fd.pth
fi

cd "$ROOT"

echo "3) Set WAV2LIP_REPO env in .env (or export now) -> ${REPO_DIR}"
echo "You can run: export WAV2LIP_REPO=${REPO_DIR}"

echo "Setup complete. Models saved to ${REPO_DIR}/checkpoints"
