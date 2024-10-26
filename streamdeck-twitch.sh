#!/bin/bash
# Wrapper script using streamlink+ffmpeg to feed video from Twitch to video.py
VIDEO=$(dirname "$0")/video.py
SIZE=$(python3 $VIDEO dimensions|sed 's/x/:/')
FPS=10

streamlink --loglevel none $1 360p,worst --stdout \
    | ffmpeg -loglevel -8 -i - \
    -vf "scale=${SIZE}:force_original_aspect_ratio=increase,crop=${SIZE},fps=${FPS}" -vcodec rawvideo -pix_fmt rgb24 -f rawvideo - \
    -vn -acodec pcm_s32le -f pulse -name "streamdeck-twitch" default \
    |python3 $VIDEO play --no-frameskipping --fps ${FPS}
