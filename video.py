#!/usr/bin/env python3
import sys
import threading
import time

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeck import StreamDeck
from StreamDeck.Devices.StreamDeckOriginal import StreamDeckOriginal
from StreamDeck.ImageHelpers import PILHelper


# -vf "scale=504:288:force_original_aspect_ratio=increase,crop=504:288"
# img = Image.frombytes('RGB', (width, height), in_bytes)

# ffmpeg -i bunny_640_5s.m4v -vf "scale=504:288:force_original_aspect_ratio=increase,crop=504:288" -vcodec rawvideo -pix_fmt rgb24 -f rawvideo bunny_scaled.rgbframes

def spacing(deck: StreamDeck):
    default_spacing = (36, 36)
    return {
        StreamDeckOriginal.DECK_TYPE: (36, 36),
    }.get(deck.deck_type, default_spacing)

def determine_size(deck: StreamDeck):
    key_spacing = spacing(deck)
    image_format = deck.key_image_format()
    rows, cols = deck.key_layout()
    return (cols*image_format['size'][0] + (cols-1)*key_spacing[0],
            rows*image_format['size'][1] + (rows-1)*key_spacing[1])

# Crops out a key-sized image from a larger deck-sized image, at the location
# occupied by the given key index.
def crop_key_image_from_deck_sized_image(deck, image, key_spacing, key):
    key_rows, key_cols = deck.key_layout()
    key_width, key_height = deck.key_image_format()['size']
    spacing_x, spacing_y = key_spacing

    # Determine which row and column the requested key is located on.
    row = key // key_cols
    col = key % key_cols

    # Compute the starting X and Y offsets into the full size image that the
    # requested key should display.
    start_x = col * (key_width + spacing_x)
    start_y = row * (key_height + spacing_y)

    # Compute the region of the larger deck image that is occupied by the given
    # key, and crop out that segment of the full image.
    region = (start_x, start_y, start_x + key_width, start_y + key_height)
    segment = image.crop(region)

    # Create a new key-sized image, and paste in the cropped section of the
    # larger image.
    key_image = PILHelper.create_key_image(deck)
    key_image.paste(segment)

    return PILHelper.to_native_key_format(deck, key_image)


# Closes the StreamDeck device on key state change.
def key_change_callback(deck, key, state):
    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Reset deck, clearing all button images.
        deck.reset()

        # Close deck handle, terminating internal worker threads.
        deck.close()


if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()
    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    for index, deck in enumerate(streamdecks):
        # This example only works with devices that have screens.
        if not deck.is_visual():
            continue
        deck.open()
        print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))

        deck.reset()

        size = determine_size(deck)
        print(size)

        # Register callback function for when a key state changes.
        deck.set_key_callback(key_change_callback)

        i = 0
        while True:
            #image = Image.open(fn)
            image = Image.frombytes('RGB', size, sys.stdin.buffer.read(size[0]*size[1]*3))
            key_spacing = spacing(deck)

            key_images = dict()
            for k in range(deck.key_count()):
                key_images[k] = crop_key_image_from_deck_sized_image(deck, image, key_spacing, k)

            # Use a scoped-with on the deck to ensure we're the only thread
            # using it right now.
            with deck:
                # Draw the individual key images to each of the keys.
                for k in range(deck.key_count()):
                    key_image = key_images[k]

                    # Show the section of the main image onto the key.
                    deck.set_key_image(k, key_image)
