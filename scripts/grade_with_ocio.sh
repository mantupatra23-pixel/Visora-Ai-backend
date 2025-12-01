#!/bin/bash
# scripts/grade_with_ocio.sh
# Usage: ./grade_with_ocio.sh /path/to/in_%04d.exr /path/to/lut.cube /path/to/out_%04d.png 25
INPAT=$1
LUT=$2
OUTPAT=$3
FPS=${4:-25}
# Use ffmpeg lut3d for .cube LUTs
ffmpeg -y -r $FPS -i "$INPAT" -vf "lut3d=file='$LUT'" -c:v libx264 -crf 18 -pix_fmt yuv420p temp_video.mp4
# optionally extract frames
ffmpeg -i temp_video.mp4 -vf fps=$FPS "$OUTPAT"
echo "Grading complete. output written to temp_video.mp4 and frames $OUTPAT"
