#!/usr/bin/env bash
# scripts/run_weather_pipeline.sh
# Usage: ./run_weather_pipeline.sh /full/path/to/job.json /full/path/to/outdir
set -euo pipefail
JOBFILE="$1"
OUTDIR="$2"
BLENDER_BIN="${BLENDER_BIN:-blender}"
FFMPEG_BIN="${FFMPEG_BIN:-ffmpeg}"
TMPDIR="${OUTDIR}/tmp"
mkdir -p "$OUTDIR" "$TMPDIR"

echo "JOBFILE: $JOBFILE"
echo "OUTDIR : $OUTDIR"

# 1) Run base weather baker
echo "[1/5] Running base weather baker..."
"$BLENDER_BIN" --background --python blender_scripts/weather_baker.py -- "$JOBFILE" "$OUTDIR" > "${OUTDIR}/base_baker.log" 2>&1 || { echo "Base baker failed. Check ${OUTDIR}/base_baker.log"; exit 1; }

# 2) Optional: FLIP (based on job features/flip_preset)
if grep -q '"flip"' "$JOBFILE" || grep -q '"flip_fluid"' "$JOBFILE"; then
  echo "[2/5] Running FLIP fluid sim (may be long)..."
  "$BLENDER_BIN" --background --python blender_scripts/weather_flip_fluid.py -- "$JOBFILE" "$OUTDIR" > "${OUTDIR}/flip.log" 2>&1 || echo "FLIP step failed (non-fatal) - see ${OUTDIR}/flip.log"
else
  echo "[2/5] No FLIP requested, skipping."
fi

# 3) Optional: Lightning + thunder audio
if grep -q '"lightning_audio"' "$JOBFILE" || grep -q '"lightning_flashes"' "$JOBFILE"; then
  echo "[3/5] Generating lightning & thunder audio..."
  "$BLENDER_BIN" --background --python blender_scripts/weather_lightning_audio.py -- "$JOBFILE" "$OUTDIR" > "${OUTDIR}/lightning.log" 2>&1 || echo "Lightning step failed - see ${OUTDIR}/lightning.log"
else
  echo "[3/5] No lightning_audio requested, skipping."
fi

# 4) Optional puddles
if grep -q '"puddles"' "$JOBFILE"; then
  echo "[4/5] Creating puddles and wet reflections..."
  "$BLENDER_BIN" --background --python blender_scripts/weather_puddles.py -- "$JOBFILE" "$OUTDIR" > "${OUTDIR}/puddles.log" 2>&1 || echo "Puddles step failed - see ${OUTDIR}/puddles.log"
else
  echo "[4/5] No puddles requested, skipping."
fi

# 5) Optional transition timeline
if grep -q '"transition"' "$JOBFILE"; then
  echo "[5/5] Applying transition timeline..."
  "$BLENDER_BIN" --background --python blender_scripts/weather_transition.py -- "$JOBFILE" "$OUTDIR" > "${OUTDIR}/transition.log" 2>&1 || echo "Transition step failed - see ${OUTDIR}/transition.log"
else
  echo "[5/5] No transition requested, skipping."
fi

# Post-process: if thunder audio exists, mux with frames to mp4; otherwise create silent mp4
AUDIO_MANIFEST="${OUTDIR}/$(basename $(jq -r '.job_id' $JOBFILE 2>/dev/null || echo job))_audio_manifest.json"
# try to find any thunder wav (created by lightning script) or any wav in outdir
THUNDER_WAV=$(ls "${OUTDIR}"/*thunder*.wav 2>/dev/null | head -n1 || true)

# find rendered frames pattern (frame_0001.png etc)
FRAME_GLOB=$(ls "${OUTDIR}"/frame_* 2>/dev/null | head -n1 || true)
if [ -z "$FRAME_GLOB" ]; then
  echo "No frames found in $OUTDIR — checking for exported video/FBX..."
else
  # derive frame pattern
  FRAME_PATTERN=$(basename "$FRAME_GLOB")
  # replace numbers with %04d
  FRAME_PATTERN=${FRAME_PATTERN//0/\\%0}
  # fallback: explicit pattern frame_%04d.png
  FRAME_PATTERN="frame_%04d.png"
  if [ -n "$THUNDER_WAV" ]; then
    echo "Muxing frames with thunder audio -> ${OUTDIR}/final_with_thunder.mp4"
    "$FFMPEG_BIN" -y -r 24 -i "${OUTDIR}/frame_%04d.png" -i "$THUNDER_WAV" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "${OUTDIR}/final_with_thunder.mp4" > "${OUTDIR}/ffmpeg_mux.log" 2>&1 || echo "ffmpeg mux failed"
  else
    echo "No thunder audio found — creating silent mp4 -> ${OUTDIR}/final.mp4"
    "$FFMPEG_BIN" -y -r 24 -i "${OUTDIR}/frame_%04d.png" -c:v libx264 -pix_fmt yuv420p -an "${OUTDIR}/final.mp4" > "${OUTDIR}/ffmpeg_mux.log" 2>&1 || echo "ffmpeg render failed"
  fi
fi

echo "Pipeline complete. Output in $OUTDIR"
