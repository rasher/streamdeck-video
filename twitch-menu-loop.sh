#!/bin/bash

while true; do
    url=$($(dirname "$0")/twitch-menu.py $1)
    if [ "$url" == "exit" ]; then
        exit 0
    elif [ ! -z "$url" ]; then
        echo "Playing $url"
        $(dirname "$0")/streamdeck-twitch.sh $url
    fi
done
