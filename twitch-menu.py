#!/usr/bin/env python3
import os
import time
import traceback
from datetime import timedelta
from io import BytesIO
from typing import Dict

import requests
import requests_cache
from PIL import Image, ImageEnhance
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeck import StreamDeck
from StreamDeck.ImageHelpers import PILHelper
from dotenv import load_dotenv
from requests import Session
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from video import draw_image, spacing, determine_size

load_dotenv()  # take environment variables from .env.

SCOPES = [AuthScope.USER_READ_FOLLOWS]

keys = []
keep_looping = [True]


async def get_team_users_and_streams(twitch: Twitch, teamname) -> Dict:
    team = await twitch.get_teams(name=teamname)
    ids = [u.user_id for u in team.users]
    users = twitch.get_users(user_ids=ids)
    result = {}
    async for user in users:
        result[user.id] = [user, None]
    streams = twitch.get_streams(user_id=ids)
    async for stream in streams:
        result[stream.user_id][1] = stream
    return result


def get_thumbnail(session: Session, url, is_live):
    resp = session.get(url)
    resp.raise_for_status()
    thumbnail = Image.open(BytesIO(resp.content), formats=("JPEG", "PNG"))
    if not is_live:
        converter = ImageEnhance.Color(thumbnail)
        thumbnail = converter.enhance(0.10)
    return thumbnail


def user_sort(u):
    return 0 if u[1] is not None else 1, u[0].display_name.lower()


async def key_pressed(deck: StreamDeck, key, state):
    if state == False:
        return
    if keys[key] is not None:
        user, stream = keys[key]
        keep_looping[0] = False
        key_spacing = spacing(deck)
        size = determine_size(deck, key_spacing)
        if stream is not None:
            url = stream.thumbnail_url.replace("{width}", str(size[0])).replace("{height}", str(size[1]))
            resp = requests.get(url)
            video_thumb = Image.open(BytesIO(resp.content), formats=("JPEG", "PNG"))
            draw_image(deck, video_thumb, key_spacing)
            print("https://twitch.tv/{u.login}".format(u=user))
        else:
            twitch: Twitch = deck._twitch
            video = await first(twitch.get_videos(user_id=user.id, first=1))
            if video:
                print(video.url)
                try:
                    url = video.thumbnail_url.replace("%{width}", str(size[0])).replace("%{height}", str(size[1]))
                    resp = requests.get(url)
                    video_thumb = Image.open(BytesIO(resp.content), formats=("JPEG", "PNG"))
                    draw_image(deck, video_thumb, key_spacing)
                except Exception as e:
                    traceback.print_exc()
    else:
        deck.reset()
        print("exit")
    deck.close()
    sys.exit(0)


async def main(teamname):
    twitch = await Twitch(os.getenv('CLIENT_ID'), os.getenv('CLIENT_SECRET'))
    helper = UserAuthenticationStorageHelper(twitch, SCOPES)
    await helper.bind()
    streamdecks = DeviceManager().enumerate()
    deck: StreamDeck = streamdecks[0]
    deck.open()
    deck.reset()
    deck._twitch = twitch
    keys.extend([None]*deck.key_count())
    deck.reset()
    deck.set_key_callback_async(key_pressed, asyncio.get_running_loop())

    while keep_looping[0]:
        if not deck.is_open():
            break
        users_and_streams = await get_team_users_and_streams(twitch, teamname)
        with requests_cache.CachedSession('twitch-menu', expire_after=timedelta(hours=6)) as s:
            for k, (user, stream) in enumerate(sorted(users_and_streams.values(), key=user_sort)):
                thumb = get_thumbnail(s, user.profile_image_url, False if stream is None else True)
                key_image = PILHelper.create_scaled_key_image(deck, thumb)
                deck.set_key_image(k, PILHelper.to_native_key_format(deck, key_image))
                keys[k] = user, stream
        time.sleep(3)
    deck.close()


if __name__ == '__main__':
    import sys
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(sys.argv[1]))
