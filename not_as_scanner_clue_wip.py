"""
CLUE Circuit Python Color Patchwork Demo

This demo display a number of colourfull square on the CLUE.
The number of square available grow dynamically based on the need.
It is optimised for efficiency on displayio:
* a bitmap bitmap is created containing unique color from a palette for each pixel_shader
* to display on the full screen, the scalling option is used
* changing the color of one square only require to change the right color in the palette

Currently the size can only increase, but option to resqueeze if less square are need is investigated
"""

import time
import random
import board
from adafruit_clue import clue
import displayio

MAX_COLOR = 225

COLOR_TRANSPARENT_INDEX = 0
COLOR_OFFWHITE_INDEX = 1


# The color pickers will cycle through this list with buttons A and B.
color_options = [0xEE0000,
                 0xEEEE00,
                 0x00EE00,
                 0x00EEEE,
                 0x0000EE,
                 0xEE00EE,
                 0xCCCCCC,
                 0xFF9999,
                 0x99FF99,
                 0x9999FF]


display = board.DISPLAY

max_color = [1, 5, 10, 17, 26, 37, 65, 101, 145, 226]
side_color = [1, 2, 3, 4, 5, 6 , 8, 10, 12, 15]
scale_color = [240, 120, 80, 60, 48, 40, 30, 24, 20, 16]


"""
Filling using a growing pattern.
Only works on square.
Each position get a unique palette colour.
"""
def prefil_bitmap(my_bitmap):
#    print(bitmap.width, bitmap.height)
    val = 2
    for limit in range(0, my_bitmap.width):
        if (limit % 2) == 0:
            for i in range(0, limit):
                my_bitmap[i, limit] = val
                val = val + 1
            for j in range(limit, -1, -1):
                my_bitmap[limit, j] = val
                val = val + 1
        else:
            for i in range(0, limit):
                my_bitmap[limit, i] = val
                val = val + 1
            for j in range(limit, -1, -1):
                my_bitmap[j, limit] = val
                val = val + 1



# Create a bitmap with two colors + 36 colors for the palette_mapping
bitmap = displayio.Bitmap(6, 6, 36 + 2)

# Pre-fill the bitmap with 38 colors (color 0 and 1 are reserved)
prefil_bitmap(bitmap)

# Create an empty palette that will be used in one to one mapping
palette_mapping = displayio.Palette(MAX_COLOR + 3)


def make_transparent():
    palette_mapping.make_transparent(0)
    for i in range(0, bitmap.height):
        for j in range(0, bitmap.width):
            bitmap[i, j] = 0


def make_white():
    for i in range (2, MAX_COLOR + 2):
        palette_mapping[i] = 0xFFFFFF


def make_black():
    for i in range (2, MAX_COLOR + 2):
        palette_mapping[i] = 0x000000


def make_palette():
    palette_mapping[0] = 0x000000
    palette_mapping[1] = 0xFFFFFF
    for i, color in enumerate(nearby_colors): ### This might crash if above 100 ###
        palette_mapping[i+2] = color


# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette_mapping)
patchwork_group = displayio.Group(scale=30)
patchwork_group.append(tile_grid)
# Create a Group
group = displayio.Group()
# Add the TileGrid to the Group
group.append(patchwork_group)
# Add the Group to the Display
display.show(group)


nearby_colors = [0x888888]

max_color = [1, 5, 10, 17, 26, 37, 65, 101, 145, 226]
side_color = [1, 2, 3, 4, 5, 6 , 8, 10, 12, 15]
scale_color = [240, 120, 80, 60, 48, 40, 30, 24, 20, 16]


best_resolution = -1
def adapt_resolution(to_fit):
    global best_resolution, patchwork_group, tile_grid, bitmap
    # Check the best resolution we should use for 'to_fit' element.
    best = 0
    for i, max_c in enumerate(max_color):
        best = i
        if max_c > to_fit:
            break
    # Rebuild a new bitmap scale if needed
    if best_resolution!=best:
        group.remove(patchwork_group)
        bitmap = displayio.Bitmap(side_color[best], side_color[best], max_color[best] + 1)
        prefil_bitmap(bitmap)
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette_mapping)
        patchwork_group = displayio.Group(scale=scale_color[best])
        patchwork_group.append(tile_grid)
        group.append(patchwork_group)

    best_resolution=best


size_to_fit = len(nearby_colors)
adapt_resolution(size_to_fit)


def draw_grid():
    for i, color in enumerate(nearby_colors):
        if i <= MAX_COLOR:
            palette_mapping[i+2] = color & 0xFFFFFF ### Mask 0xFFFFFF to avoid invalid color.


def add_fake():
    fake_color = random.choice(color_options)
    nearby_colors.append(fake_color)


make_black()
draw_grid()

while True:
    add_fake()

    size_to_fit = len(nearby_colors)
    adapt_resolution(size_to_fit)
    draw_grid()
    time.sleep(1)
