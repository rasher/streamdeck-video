#!/usr/bin/env python3
import sys
import time
from fractions import Fraction

import click
import typer
from PIL import Image, ImageDraw
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices.StreamDeck import StreamDeck
from StreamDeck.Devices.StreamDeckOriginal import StreamDeckOriginal
from StreamDeck.ImageHelpers import PILHelper
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

app = typer.Typer()


def spacing(deck: StreamDeck):
    default = [22, 22]
    return {
        StreamDeckOriginal.DECK_TYPE: [22, 22],
        # TODO: Add other types
    }.get(deck.deck_type(), default)


def determine_size(deck: StreamDeck, key_spacing = None):
    if key_spacing is None:
        key_spacing = spacing(deck)
    image_format = deck.key_image_format()
    rows, cols = deck.key_layout()
    return (cols * image_format['size'][0] + (cols - 1) * key_spacing[0],
            rows * image_format['size'][1] + (rows - 1) * key_spacing[1])


# Crops out a key-sized image from a larger deck-sized image, at the location
# occupied by the given key index.
def crop_key_image_from_deck_sized_image(deck: StreamDeck, image, key_spacing, key):
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


def draw_image(deck, image, key_spacing):
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
            if deck.is_open():
                deck.set_key_image(k, key_image)

def cb_close_on_any(deck, key, state):
    """Closes the StreamDeck device on any keypress state change."""
    with deck:
        deck.reset()
        deck.close()


def fraction(s: str) -> Fraction:
    return Fraction(s)


class DeckParam(click.ParamType):
    name = "deck"

    def convert(self, value, param, ctx) -> StreamDeck:
        found_deck = None
        for idx, candidate in enumerate(DeviceManager().enumerate()):
            if value.isdigit() and int(value) == idx:
                found_deck = candidate
                break
            elif value == candidate.deck_type():
                found_deck = candidate
                break
            elif value == candidate.device.path():
                found_deck = candidate
                break
            candidate.open()
            if value == candidate.get_serial_number():
                found_deck = candidate
                candidate.close()
                break
            candidate.close()

        if found_deck is None:
            self.fail(f"Stream Deck '{value}' not found", param, ctx)
        elif not found_deck.is_visual():
            self.fail("Non-visual deck: {}".format(found_deck.deck_type()), param, ctx)

        return found_deck

DECK_PARAM = DeckParam()
DECK_HELP = "Select deck to use. Value may be either index, type, USB path or serial no. (see the list command)"


def create_test_pattern(size) -> Image:
    im = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(im)
    colors = ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow']
    line = [[float(0), float(0)], [float(size[1]), float(size[1])]]
    line[0][0] -= size[1]
    line[1][0] -= size[1]
    while line[0][0] < size[1]*2:
        draw.line([tuple(line[0]), tuple(line[1])], fill=colors[0], width=15)
        line[0][0] += 25
        line[1][0] += 25
        colors.append(colors.pop(0))
    return im


@app.command()
def spacing_test(deck: Annotated[StreamDeck, typer.Option(click_type=DECK_PARAM, help=DECK_HELP)] = '0'):
    """Display a test pattern. Buttons 1-4 adjust spacing. Used for testing"""

    def print_sizing(deck):
        image_size = determine_size(deck, key_spacing)
        print("Key spacing: {0[0]}x{0[1]}, image size: {1[0]}x{1[1]}".format(key_spacing, image_size))

    def cb_test_pattern(deck, key, state):
        if key == 0 and state == True:
            key_spacing[0] -= 1
        if key == 1 and state == True:
            key_spacing[0] += 1
        if key == 2 and state == True:
            key_spacing[1] -= 1
        if key == 3 and state == True:
            key_spacing[1] += 1
        elif key > 3:
            deck.reset()
            deck.close()
            deck._streamdeck_test_run = False
        if state == True and key in [0,1,2,3]:
            print_sizing(deck)

    deck.open()
    key_spacing = spacing(deck)
    deck._streamdeck_test_run = True

    deck.set_key_callback(cb_test_pattern)
    print_sizing(deck)
    while deck._streamdeck_test_run:
        size = determine_size(deck, key_spacing)
        draw_image(deck, create_test_pattern(size), key_spacing)
        time.sleep(1)
    if deck.is_open():
        deck.reset()
        deck.close()

@app.command()
def dimensions(deck: Annotated[StreamDeck, typer.Option(click_type=DECK_PARAM, help=DECK_HELP)] = '0'):
    """Output dimensions of specified Stream Deck"""
    key_spacing = spacing(deck)
    image_size = determine_size(deck, key_spacing)
    print("{}x{}".format(*image_size))


@app.command()
def list():
    """List all available Stream Decks"""
    streamdecks = DeviceManager().enumerate()
    console = Console()
    table = Table("No.", "Type", "Serial", "USB Path", "Dimensions", "Spacing")
    for index, deck in enumerate(streamdecks):
        key_spacing = spacing(deck)
        dimensions = determine_size(deck, key_spacing)
        dim_str = "{}x{}".format(*dimensions)
        spacing_str = "{}x{}".format(*key_spacing)
        try:
            deck.open()
            table.add_row(str(index), deck.deck_type(), deck.get_serial_number(), deck.device.path(), dim_str,
                          spacing_str)
            deck.reset()
            deck.close()
        except Exception as e:
            table.add_row(str(index), deck.deck_type(), 'Unknown', deck.device.path(), dim_str, spacing_str)
    if table.row_count > 0:
        console.print(table)
    else:
        print("No Stream Decks found")


@app.command()
def play(fps: Annotated[Fraction, typer.Option(parser=fraction, help="Target FPS (supports fractions)")] = '10/1',
         frameskipping: Annotated[bool, typer.Option(help="Attempt to skip frames if lagging behind")] = True,
         deck: Annotated[StreamDeck, typer.Option(click_type=DECK_PARAM, help=DECK_HELP)] = '0'
         ):
    """
    Play video on your Streamdeck. Sure why not, that seems like a reasonable thing to do.

    Expects appropriately-sized raw rgb24 video frames on stdin.
    """
    deck.open()

    key_spacing = spacing(deck)
    image_size = determine_size(deck, key_spacing)

    # Register callback function for when a key state changes.
    deck.set_key_callback(cb_close_on_any)
    frame_time = Fraction(1, fps)
    next_frame = Fraction(time.monotonic())

    image_byte_count = image_size[0] * image_size[1] * 3
    while True:
        image_bytes = sys.stdin.buffer.read(image_byte_count)
        next_frame += frame_time
        if Fraction(time.monotonic()) > next_frame and frameskipping:
            # We're behind, skip this frame
            continue
        if len(image_bytes) == image_byte_count:
            image = Image.frombytes('RGB', image_size, image_bytes)

            try:
                draw_image(deck, image, key_spacing)
            except Exception as e:
                break
        else:
            # We read something that wasn't a full frame. No point continuing.
            deck.reset()
            deck.close()
            break
        if not deck.is_open():
            # We somehow lost connection. Panic.
            break

        sleep_interval = float(next_frame) - time.monotonic()
        if sleep_interval >= 0:
            time.sleep(sleep_interval)


if __name__ == "__main__":
    app()
