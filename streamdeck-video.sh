#!/bin/sh
# Wrapper script using ffmpeg to feed video file to video.py
VIDEO=$(dirname "$0")/video.py
SIZE=$(python3 $VIDEO dimensions|sed 's/x/:/')
FPS=$(ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate "$1")

ffmpeg -y -i "$1" \
    -vf "scale=${SIZE}:force_original_aspect_ratio=increase,crop=${SIZE}" -vcodec rawvideo -pix_fmt rgb24 -f rawvideo - \
    -vn -acodec pcm_s32le -f pulse -name $(basename "$0") default \
    | python3 $VIDEO play --frameskipping --fps $FPS
