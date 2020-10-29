### CoronAlert Scanner for CLUE
### Listen to Contact Tracing message and display the number phones nearby simultaneous in 3 different ways:
### (1) CLUE graphic mode with 16 big square pixels
### (2) NeoPixel connected to the CLUE P2 (like on a SnowPi RGB)
### (3) NeoTrellis connected to the CLUE (connected over I2C)

### Version demonstrated in Show and Tell 

### Copy this file to CLUE board as code.py

### Tested with CLUE:
### Adafruit CircuitPython 6.0.0-rc.0 on 2020-10-16; Adafruit CLUE nRF52840 Express with nRF52840

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

### Copyright (c) 2020 David Glaude

### Original code and licence

### MIT License

### Copyright (c) 2020 Kevin J. Walters

### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:

### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.

### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.

import os
import time
import busio
import board
import random

import neopixel
from adafruit_clue import clue
import displayio
from adafruit_neotrellis.neotrellis import NeoTrellis

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import Advertisement


### This is the value used when we don't know what RGB LED to use yet
NO_IDX = -3
### Address that do not advertise anymore get a very low RSSI to indicate that
NOT_RSSI = -127

### This is just to show then CPE start (or restart)
BRIGHTNESS = 1

### The number of rows is also the number of NEOPIXEL
###rows = 10 ### CPB with build in 10 RGB
###rows = 12 ### CLUE with SnowPi RGB
###rows = 16 ### CLUE with NeoTrellis
###rows = 4 ### CLUE initial value for big square pixel
rows = 16 ### Common value for NeoTrellis, Neopixel and CLUE screen


### vvv NeoPixel vvv ###
#strip = neopixel.NeoPixel(board.P2, rows, brightness=BRIGHTNESS)     ### CPB
neo_strip = neopixel.NeoPixel(board.P2, rows, brightness=BRIGHTNESS)           ### CLUE with SnowPi RGB
### ^^^ NeoPixel ^^^ ###


### vvv NeoTrellis vvv ###
# create the i2c_bus object if I2C bus is not in use yet
#i2c_bus = busio.I2C(board.SCL, board.SDA)

TRELLIS_PRESENT = True

if TRELLIS_PRESENT:
    # create the i2c object that works with Clue library
#    i2c_bus = clue._i2c
    i2c_bus = board.I2C()
    # create the trellis
    trellis = NeoTrellis(i2c_bus)



last_seen_update_ns = time.monotonic_ns()
# Reintroduce screen_update_ns to limit call to change color
screen_update_ns = 250 * 1000 * 1000

### If no advertisement received for 'hide_time_ns' that RGB LED turn BLUE and will be forgotten
hide_time_ns =      20 * 1000 * 1000 * 1000
### If no advertisement is received for 'stale_time_ns' that RGB LED is flushed for reuse
stale_time_ns =    200 * 1000 * 1000 * 1000
scan_time_s = 10

ble = BLERadio()
ble.name = "CPB"

### An array of timestamp and advertisement by key (addr)
last_ad_by_key = {}

MINI_BLUE = (0, 0, 1)

SHADE_BLUE = [
    (0, 0, 255),
    (0, 0, 127),
    (0, 0, 63),
    (0, 0, 31),
    (0, 0, 15),
    (0, 0, 7),
    (0, 0, 3),
    (0, 0, 1),
    ]

TIME_BLUE = [
    40 * 1000 * 1000 * 1000,
    60 * 1000 * 1000 * 1000,
    80 * 1000 * 1000 * 1000,
    100 * 1000 * 1000 * 1000,
    120 * 1000 * 1000 * 1000,
    140 * 1000 * 1000 * 1000,
    160 * 1000 * 1000 * 1000,
    180 * 1000 * 1000 * 1000,
    ]

RSSI_DEFAULT_COLOR = (63, 0, 0)
#RSSI_COLOR = [(0, 31, 0), (15, 31, 0), (15, 15, 0), (31, 15, 0), (31, 0, 0), (63, 0, 0)]
RSSI_COLOR = [(0, 255, 0), (127, 255, 0), (127, 127, 0), (255, 127, 0), (255, 191, 0), (255, 0, 0)]
RSSI_VALUE = [-80, -75, -70, -65, -60, -55]


### Decide color based on rssi and age_ns
def gimme_color(age_ns, rssi):
    if rssi == NOT_RSSI:
        result_color = MINI_BLUE
        for i in range(len(TIME_BLUE)):
            if age_ns < TIME_BLUE[i]:
                result_color = SHADE_BLUE[i]
                break
    else:
        result_color = RSSI_DEFAULT_COLOR
        for i in range(len(RSSI_VALUE)):
            if rssi < RSSI_VALUE[i]:
                result_color = RSSI_COLOR[i]
                break
    return ( result_color )


def delete_very_old(rows_n, ad_by_key):
    """Delete older key above the number of rows_n"""
    ### If we have more entry than space
    if len(ad_by_key)>rows_n:
        ### Sort by last seen to identify earliest that should be cleaned
        sorted_data = sorted(ad_by_key.items(), key=lambda item: (item[1][1]))
        ### Number of entries to remove
        to_delete = len(ad_by_key)-rows_n
        ### Iterate on the first entry and delete them from the list received
        for key, value in sorted_data[:to_delete]:
            ### Delete such entry
            del ad_by_key[key]


def hide_old(ad_by_key, hide_time_ns):
    """Hide any entry in the ad_by_key dict with a timestamp older than hide_time_ns. (setting RSSI to -255)"""
    ### the list() is needed to make a real list from the iterator
    ### which allows modification of the dict inside the loop
    for key, value in list(ad_by_key.items()):
        if value[1] < hide_time_ns:
            ad_by_key[key] = (value[0], value[1], NOT_RSSI, value[3])


def remove_old(ad_by_key, expire_time_ns):
    """Delete any entry in the ad_by_key dict with a timestamp older than expire_time_ns."""
    ### the list() is needed to make a real list from the iterator
    ### which allows modification of the dict inside the loop
    for key, value in list(ad_by_key.items()):
        if value[1] < expire_time_ns:
            del ad_by_key[key]



MAX_COLOR = 225

COLOR_TRANSPARENT_INDEX = 0
COLOR_OFFWHITE_INDEX = 1

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
bitmap = displayio.Bitmap(4, 4, 16 + 2)
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
    for i, color in enumerate(array_of_pixels): ### This might crash if above 100 ###
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

array_of_pixels = [0x888888]*rows

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


def draw_grid():
    for i, color in enumerate(array_of_pixels):
        if i <= MAX_COLOR:
            palette_mapping[i+2] = color
#            palette_mapping[i+2] = color & 0xFFFFFF ### Mask 0xFFFFFF to avoid invalid color.


def update_screen(rows_n, ad_by_key, then_ns):
    """Colour is used to indicate the power of the signal or absence or recent signal."""
####    possible = list(range(rows_n))
    possible = list ( range (rows_n-1,-1,-1) )
    ### Sort by the MAC field
    sorted_data = sorted(ad_by_key.items(), key=lambda item: (item[0]))

    ### Scan all element and see what index are already in use
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        if index_col != NO_IDX:
            possible.remove(index_col)

    ### Scan all element and attribute index for those without one
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        if index_col == NO_IDX:
            new_index=possible.pop()
            ad_by_key[key] = (ad, ad_time_ns, rssi, new_index)

    ### Scan all element to display the color
    sorted_data = sorted(ad_by_key.items(), key=lambda item: (item[0]))
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        age_ns = then_ns - ad_time_ns
        pixel_color=gimme_color(age_ns, rssi)
        little_index=index_col & 0xFF
        neo_strip[index_col]=pixel_color
        if TRELLIS_PRESENT:
            trellis.pixels[index_col]=pixel_color
        array_of_pixels[little_index]=pixel_color
        time.sleep(0.01)

    ### Scan unused index to clear the color
    for index in possible:
        neo_strip[index]=(0, 0, 0)
        if TRELLIS_PRESENT:
            trellis.pixels[index]=(0, 0, 0)
        array_of_pixels[index]=(0, 0, 0)
        time.sleep(0.01)
    draw_grid()


size_to_fit = len(array_of_pixels)
adapt_resolution(size_to_fit)


#make_black()
make_white()
draw_grid()

# cycle the LEDs on startup
for i in range(16):
    array_of_pixels[i] = (0, 0, 255)
    draw_grid()
    if TRELLIS_PRESENT:
        trellis.pixels[i] = (0, 0, 31)
    neo_strip[i]=(0, 0, 31)
    time.sleep(0.05)
for i in range(16):
    array_of_pixels[i] = (0, 0, 0)
    draw_grid()
    if TRELLIS_PRESENT:
        trellis.pixels[i] = (0, 0, 0)
    neo_strip[i]=(0, 0, 0)
    time.sleep(0.05)
draw_grid()


while True:
    ### For all the advertisement
    for ad in ble.start_scan(minimum_rssi=-127, timeout=scan_time_s):
        ### Take the timestamp
        now_ns = time.monotonic_ns()
        ### If this is a contact tracing advertisement
        if 3 in ad.data_dict:
            if ad.data_dict[3] == b'o\xfd':
                ### Found a Contact Tracing advertisement.
                addr_text = "".join(["{:02x}".format(b) for b in reversed(ad.address.address_bytes)])
                if addr_text in last_ad_by_key:
                    ### Updating existing entry with a new timestamp
                    last_ad_by_key[addr_text] = (ad, now_ns, ad.rssi, last_ad_by_key[addr_text][3])
                else:
                    ### Creating a new entry, but we don't know what RGB LED to use yet, so NO_IDX
                    last_ad_by_key[addr_text] = (ad, now_ns, ad.rssi, NO_IDX)
        delete_very_old(rows, last_ad_by_key)
        hide_old(last_ad_by_key, time.monotonic_ns() - hide_time_ns)
        remove_old(last_ad_by_key, time.monotonic_ns() - stale_time_ns)
        if now_ns - last_seen_update_ns > screen_update_ns:
            update_screen(rows, last_ad_by_key, now_ns)
            last_seen_update_ns = now_ns

### This code permit to adapt the number of Square displayed on the Clue screen
#    size_to_fit = len(nearby_colors)
#    adapt_resolution(size_to_fit)
#    draw_grid()
#    time.sleep(1)
