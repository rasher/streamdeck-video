# video.py

This will play a video on a streamdeck.

You must feed it raw video frames of the right size on stdin. You can use
FFMPEG for this. Example (for an original Streamdeck):

```shell
ffmpeg -i BigBuckBunny_640x360.m4v \
  -vf "scale=448:260:force_original_aspect_ratio=increase,crop=448:260" \
  -vcodec rawvideo -pix_fmt rgb24 -f rawvideo - \
  | ./video.py play --fps 24
```

Two wrapper scripts are included to help with this, `streamdeck-twitch.sh` and `streamdeck-video.sh`.

# twitch-menu.py

This is a completely different thing. Will read a Twitch 'team' and populate buttons with ceach member's profile
photo. Channels which are live will be shown in full colour. Clicking a member will output the URL to the member's
stream if live, or their latest VOD and exit.

You must set Client ID and Secret as Environment variables (or add them to `.env`):

    CLIENT_ID=foo
    CLIENT_SECRET=bar

With the included `twitch-menu-loop.sh` script this can give the appearance of a Stream Deck with a nice menu for
watching Twitch streams.

# Setup

Didn't do any packaging I'm afraid. Just two requirements.txt files.

- requirements.txt - for both utilities
- requirements-video.txt - if you just want the video part

# Credits

This script was made by combining the example scripts "Tiled Image" and
"Animaged Images" from the
[streamdeck Python library](https://python-elgato-streamdeck.readthedocs.io/en/stable/index.html),
with a bit of glue and polish.
