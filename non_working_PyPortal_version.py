### CoronAlert Scanner
### Listen to Contact Tracing message and display the number phones nearby
### Works on:
### (1) Circuit Bluefruit Express CoronAlert Scanner
### (2a) CLUE + SnowPi RGB CoronAlert Scanner (or other NeoPixel connected on P2)
### (2b) PyPortal + SnowPi RGB CoronAlert Scanner (connected on D4)
### (3a) CLUE + NeoTrellis CoronAlert Scanner (connected over I2C)
### (3b) PyPortal + NeoTrellis CoronAlert Scanner (connected over I2C)

### Copy this file to CPB, CLUE or PyPortal board as code.py


### Tested with Circuit Playground Bluefruit:
### Adafruit CircuitPython 6.0.0-beta.1 on 2020-10-01; Adafruit Circuit Playground Bluefruit with nRF52840

### Tested with CLUE:
### Adafruit CircuitPython 6.0.0-beta.0 on 2020-09-21; Adafruit CLUE nRF52840 Express with nRF52840

### Tested with PyPortal:
### Not working yet for PyPortal as HCI_bleio does support scanning for advertisement yet

### Copyright (c) 2020 David Glaude
### (1) Simplified version to remove the need for TFT Gizmo and work only with the 10 NeoPixel of the CPB
### (2) Also work with 12 NeoPixel from the SnowPi RGB.
### (3) Also work with 16 NeoPixel on the NeoTrellis.

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

import time
import os

import busio
import board
import neopixel
from adafruit_neotrellis.neotrellis import NeoTrellis

### https://github.com/adafruit/Adafruit_CircuitPython_BLE
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import Advertisement 


### This is the value used when we don't know what RGB LED to use yet
NO_IDX = -1
### Address that do not advertise anymore get a very low RSSI to indicate that
NOT_RSSI = -127

### This is just to show then CPE start (or restart)
BRIGHTNESS = 1

### The number of rows is also the number of NEOPIXEL
###rows = 10 ### CPB with build in 10 RGB
###rows = 12 ### CLUE with SnowPi RGB
rows = 12 ### PyPortal with SnowPi RGB
###rows = 16 ### CLUE with NeoTrellis


###strip = neopixel.NeoPixel(board.NEOPIXEL, rows, brightness=BRIGHTNESS)     ### CPB
###strip = neopixel.NeoPixel(board.P2, rows, brightness=BRIGHTNESS)           ### CLUE with SnowPi RGB
strip = neopixel.NeoPixel(board.D4, rows, brightness=BRIGHTNESS)           ### PyPortal with SnowPi RGB

# create the i2c object for the trellis
i2c_bus = busio.I2C(board.SCL, board.SDA)
# create the trellis
trellis = NeoTrellis(i2c_bus)

for i in range(16):
    trellis.pixels[i] = (0, 0, 31)
    time.sleep(0.05)

for i in range(16):
    trellis.pixels[i] = (0, 0, 0)
    time.sleep(0.05)


### Neopixel version for CPB and SnowPi
strip.fill((0, 0, 31))
time.sleep(0.5)
strip.fill((0, 0, 0))

last_seen_update_ns = time.monotonic_ns()
# Reintroduce screen_update_ns to limit call to change color
screen_update_ns = 250 * 1000 * 1000

### If no advertisement received for 'hide_time_ns' that RGB LED turn BLUE and will be forgotten
hide_time_ns =      20 * 1000 * 1000 * 1000
### If no advertisement is received for 'stale_time_ns' that RGB LED is flushed for reuse
stale_time_ns =    200 * 1000 * 1000 * 1000
scan_time_s = 10

from adafruit_airlift.esp32 import ESP32
esp32 = ESP32(tx=board.TX, rx=board.RX)
adapter = esp32.start_bluetooth()
ble = BLERadio(adapter)
ble.name = "PyPortal"

###ble = BLERadio()
###ble.name = "CPB"

### An array of timestamp and advertisement by key (addr)
last_ad_by_key = {}

MINI_BLUE = (0, 0, 1)
SHADE_BLUE = [(0, 0, 63), (0, 0, 31), (0, 0, 15), (0, 0, 7), (0, 0, 3)]
TIME_BLUE = [50 * 1000 * 1000 * 1000, 80 * 1000 * 1000 * 1000, 110 * 1000 * 1000 * 1000, 140 * 1000 * 1000 * 1000, 170 * 1000 * 1000 * 1000]

RSSI_DEFAULT_COLOR = (63, 0, 0)
RSSI_COLOR = [(0, 31, 0), (15, 31, 0), (15, 15, 0), (31, 15, 0), (31, 0, 0), (63, 0, 0)]
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


def update_screen(rows_n, ad_by_key, then_ns):
    """Colour is used to indicate the power of the signal or absence or recent signal."""
    possible = list(range(rows_n))
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
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        age_ns = then_ns - ad_time_ns
        pixel_color=gimme_color(age_ns, rssi)
###        strip[index_col]=pixel_color
        little_index=index_col & 0xFF
#        byte_index=bytes(index_col & 0xFF)
        trellis.pixels[little_index]=pixel_color
        time.sleep(0.01)

    ### Scan unused index to clear the color
    for index in possible:
###        strip[index]=(0, 0, 0)
        trellis.pixels[index]=(0, 0, 0)
        time.sleep(0.01)


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
