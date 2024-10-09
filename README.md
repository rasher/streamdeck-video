This will play a video as fast as possible on a streamdeck.

You must feed it raw video frames of the right size on stdin. You can use
FFMPEG for this. Example (for an original Streamdeck):

```shell
ffmpeg -i BigBuckBunny_640x360.m4v \
  -vf "scale=504:288:force_original_aspect_ratio=increase,crop=504:288" \
  -vcodec rawvideo -pix_fmt rgb24 -f rawvideo - \
  | ./video.py
```
If you have multiple Streamdecks, first of all what the hell, secondly, this
script will play it on the first Streamdeck with a display.
