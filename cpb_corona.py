### Circuit Bluefruit Express CoronAlert Scanner
### Listen to Contact Tracing message and display the number phones nearby

### Copy this file to CPB board as code.py

### Tested with Circuit Playground Bluefruit:
### Adafruit CircuitPython 6.0.0-alpha.2 on 2020-07-23; Adafruit Circuit Playground Bluefruit with nRF52840
### Adafruit CircuitPython 6.0.0-beta.1 on 2020-10-01; Adafruit Circuit Playground Bluefruit with nRF52840

### Copyright (c) 2020 David Glaude
### Simplified version to remove the need for TFT Gizmo and work only with the 10 NeoPixel of the CPB
### Original code from ...

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

import time
import gc
import os

import board
import neopixel
import digitalio

### https://github.com/adafruit/Adafruit_CircuitPython_BLE
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import Advertisement


### Inputs (buttons reversed as it is used upside-down with Gizmo)
_button_a = digitalio.DigitalInOut(board.BUTTON_A)
_button_a.switch_to_input(pull=digitalio.Pull.DOWN)
button_right = lambda: _button_a.value

_button_b = digitalio.DigitalInOut(board.BUTTON_B)
_button_b.switch_to_input(pull=digitalio.Pull.DOWN)
button_left = lambda: _button_b.value

_switch = digitalio.DigitalInOut(board.SLIDE_SWITCH)
_switch.switch_to_input(pull=digitalio.Pull.UP)
switch = lambda: _switch.value


# The number of rows is also the number of NEOPIXEL
rows = 10
NO_IDX = -1


### Observed value measured on CPB as advertised by my phones with CoronAlert app.
### Extreem value so that you get full red or full green (-90 to -50 give less frequently pure color)
NOT_RSSI = -127


BRIGHTNESS = 0.3
strip = neopixel.NeoPixel(board.NEOPIXEL, rows, brightness=BRIGHTNESS)
strip.fill((0, 0, 31))
time.sleep(0.5)
strip.fill((0, 0, 0))


debug = 0


def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


last_seen_update_ns = time.monotonic_ns()

screen_update_ns =        250 * 1000 * 1000
hide_time_ns =      20 * 1000 * 1000 * 1000


MINI_BLUE = (0, 0, 1)

SHADE_BLUE = [
    (0, 0, 63),
    (0, 0, 31),
    (0, 0, 15),
    (0, 0, 7),
    (0, 0, 3)
    ]

TIME_BLUE = [
    50 * 1000 * 1000 * 1000,
    80 * 1000 * 1000 * 1000,
    110 * 1000 * 1000 * 1000,
    140 * 1000 * 1000 * 1000,
    170 * 1000 * 1000 * 1000
    ]


RSSI_DEFAULT_COLOR = (0, 63, 0)

RSSI_COLOR = [
    (0, 31, 0),
    (15, 31, 0),
    (15, 15, 0),
    (31, 15, 0),
    (31, 0, 0),
    (63, 0, 0)
    ]

RSSI_VALUE = [
    -80,
    -75,
    -70,
    -65,
    -60,
    -55
    ]

NOT_RSSI = -127


OFF = (0, 0, 0)


stale_time_ns =    200 * 1000 * 1000 * 1000

scan_time_s = 10

ble = BLERadio()
ble.name = "CPB"

addresses_count = {}

### An array of timestamp and advertisement by key (addr)
last_ad_by_key = {}




### Decide color based on rssi (could use age_ns to fade out BLUE)
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


def remove_old(ad_by_key, expire_time_ns):
    """Delete any entry in the ad_by_key dict with a timestamp older than expire_time_ns."""
    ### the list() is needed to make a real list from the iterator
    ### which allows modification of the dict inside the loop
    for key, value in list(ad_by_key.items()):
        if value[1] < expire_time_ns:
            del ad_by_key[key]


def hide_old(ad_by_key, hide_time_ns):
    """Hide any entry in the ad_by_key dict with a timestamp older than hide_time_ns. (setting RSSI to -255)"""
    ### the list() is needed to make a real list from the iterator
    ### which allows modification of the dict inside the loop
    for key, value in list(ad_by_key.items()):
        if value[1] < hide_time_ns:
            ad_by_key[key] = (value[0], value[1], NOT_RSSI, value[3])


def delete_old(rows_n, ad_by_key):
    """Delete older key above the number of rows_n"""
    ### Sort by last seen to identify earliest that should be cleaned
    sorted_data = sorted(ad_by_key.items(), key=lambda item: (item[1][1]))
    ### Number of entries to remove
    to_delete = len(ad_by_key)-rows_n
    ### Iterate on the first entry and delete them from the list received
    for key, value in sorted_data[:to_delete]:
        ### Delete such entry
        del ad_by_key[key]


def byte_bounded(val):
    return (min(max(round(val) , 0), 255))






def update_screen(rows_n, ad_by_key, then_ns):
    """Update the screen with the most recently seen entries.
       The text colour is used to indicate the power of the signal
       """

    ### Sort by the MAC field
    sorted_data = sorted(ad_by_key.items(), key=lambda item: (item[0]))

    mac_no_idx = {}
    idx_in_use = {}

    ### Add the top N rows to to the screen
    ### the key is the mac address as text without any colons
    idx = 0
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        if index_col == NO_IDX:
            d_print(1, "Key: ", key, " as no index.")
            mac_no_idx[key] = 1
        else:
            try:
                idx_in_use[index_col] += 1
            except KeyError:
                idx_in_use[index_col] = 1

    d_print(1, "mac_no_idx = ", mac_no_idx)
    d_print(1, "idx_in_use = ", idx_in_use)


    ### Add the top N rows to to the screen
    ### the key is the mac address as text without any colons
    idx = 0
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        age_ns = then_ns - ad_time_ns
        pixel_color=gimme_color(age_ns, rssi)
        strip[idx]=pixel_color
        idx += 1
        # What if idx >= rows ??? Maybe this slide avoid that: sorted_data[:rows_n]

    #### Blank out any rows not populated with data
    if idx < rows_n:
        for _ in range(rows_n - idx):
            strip[_ + idx]=(0, 0, 0)
            d_print(6, "Set ", _ + idx, " to off.")


while True:
    for ad in ble.start_scan(minimum_rssi=-127, timeout=scan_time_s):
        now_ns = time.monotonic_ns()

        if 3 in ad.data_dict:
            if ad.data_dict[3] == b'o\xfd':
                addr_text = "".join(["{:02x}".format(b) for b in reversed(ad.address.address_bytes)])
                last_ad_by_key[addr_text] = (ad, now_ns, ad.rssi, NO_IDX)
                try:
                    addresses_count[addr_text] += 1
                except KeyError:
                    addresses_count[addr_text] = 1

        if button_right():
            debug_mem_free = gc.mem_free()
            print("Memfree: ", debug_mem_free)
            print("AddCount:", addresses_count)
            print("MACS", len(addresses_count))
            while button_right():
                pass

        if button_left():
            print(last_ad_by_key)
            print(ad.address, ad.rssi, ad.scan_response, ad.tx_power, ad.complete_name, ad.short_name)
            while button_left():
                pass

        if now_ns - last_seen_update_ns > screen_update_ns:
            gc.collect()
            update_screen(rows, last_ad_by_key, now_ns)
            last_seen_update_ns = now_ns

        d_print(1,
                ad.address, ad.rssi, ad.scan_response,
                ad.tx_power, ad.complete_name, ad.short_name)

    if len(last_ad_by_key)>rows:
        delete_old(rows, last_ad_by_key)
    hide_old(last_ad_by_key, time.monotonic_ns() - hide_time_ns)
    remove_old(last_ad_by_key, time.monotonic_ns() - stale_time_ns)
