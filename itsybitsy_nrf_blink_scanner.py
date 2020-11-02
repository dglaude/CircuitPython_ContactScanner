### CoronAlert Scanner
### ADAFRUIT ITSYBITSY NRF52840 EXPRESS - BLUETOOTH LE
### Listen to Contact Tracing message and blink the number phones nearby

### Copy this file to your itsybitsy NRF52840 as code.py

### Tested:
### Adafruit CircuitPython 6.0.0-rc.0 on 2020-10-16; Adafruit ItsyBitsy nRF52840 Express with nRF52840

### Copyright (c) 2020 David Glaude
### Extremly simplified version so that only one LED is needed

### Original code licence and author:

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

import board
import adafruit_dotstar as dotstar

### https://github.com/adafruit/Adafruit_CircuitPython_BLE
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import Advertisement

import digitalio

# Number of blink
BLINK_COUNT = 0
# How long we want to wait between blinking
BLINK_PAUSE_DURATION = 5
# How long we want the LED to stay on
BLINK_ON_DURATION = 0.2
# How long we want the LED to stay off
BLINK_OFF_DURATION = 0.2
# When we last changed the LED state
LAST_BLINK_TIME = -1
LAST_SLEEP_TIME = -1
# Setup the LED pin.
led = digitalio.DigitalInOut(board.BLUE_LED)
led.direction = digitalio.Direction.OUTPUT

#from adafruit_debouncer import Debouncer
#### Configure the user switch of the ItsyBitsy nRF52840
#pin = digitalio.DigitalInOut(board.SWITCH)
#pin.direction = digitalio.Direction.INPUT
#pin.pull = digitalio.Pull.UP
#switch = Debouncer(pin)


### The number of rows is also the number of NEOPIXEL (or DotStar)
rows = 10
### This is the value used when we don't know what RGB LED to use yet
NO_IDX = -1
### Address that do not advertise anymore get a very low RSSI to indicate that
NOT_RSSI = -127

### This is just to show then CPE start (or restart)
BRIGHTNESS = 1


### Pretend we have more DotStar available than the only one on the ItsyBitsy nRF52840
strip = dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.8, auto_write=True)
#strip.brightness = 0.3
#strip[0] = (0, 0, 0)
strip.fill((0, 0, 31))
time.sleep(0.5)
strip.fill((0, 0, 0))

### If no advertisement received for 'hide_time_ns' that RGB LED turn BLUE and will be forgotten
hide_time_ns =      20 * 1000 * 1000 * 1000
### If no advertisement is received for 'stale_time_ns' that RGB LED is flushed for reuse
stale_time_ns =    200 * 1000 * 1000 * 1000
scan_time_s = 10

last_seen_update_ns = time.monotonic_ns()
# Reintroduce screen_update_ns to limit call to change color
screen_update_ns = 1 * 1000 * 1000 * 1000
### Time before not blinking for a phone that does not advertise anymore
noblink_time_ns =      10 * 1000 * 1000 * 1000

ble = BLERadio()
ble.name = "ItsyBitsy"

### An array of timestamp and advertisement by key (addr)
last_ad_by_key = {}


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


def count_active(rows_n, ad_by_key, then_ns):
    """Count the number ."""
    active = 0
    ### Sort by the MAC field
    sorted_data = sorted(ad_by_key.items(), key=lambda item: (item[0]))
    ### Scan all element to display the color
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi, index_col = value
        age_ns = then_ns - ad_time_ns
        if rssi != NOT_RSSI:
            if age_ns < noblink_time_ns:
                active = active + 1
    return (active)


blink_todo = BLINK_COUNT

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
#
        delete_very_old(rows, last_ad_by_key)
        hide_old(last_ad_by_key, time.monotonic_ns() - hide_time_ns)
        remove_old(last_ad_by_key, time.monotonic_ns() - stale_time_ns)
#### This will be the number of blink

        BLINK_COUNT = count_active(rows, last_ad_by_key, now_ns)

#         value = count_active(rows, last_ad_by_key, now_ns)
# #### Not really needed to delay updating
#         if now_ns - last_seen_update_ns > screen_update_ns:
#             last_seen_update_ns = now_ns
#             BLINK_COUNT = value

#### Blinking logic without sleep, based on https://learn.adafruit.com/multi-tasking-with-circuitpython

        # Store the current time to refer to later.
        now = time.monotonic()
        if blink_todo > 0:
            if not led.value:
                # Is it time to turn on?
                if now >= LAST_BLINK_TIME + BLINK_OFF_DURATION:
                    led.value = True
                    LAST_BLINK_TIME = now
            if led.value:
                # Is it time to turn off?
                if now >= LAST_BLINK_TIME + BLINK_ON_DURATION:
                    led.value = False
                    LAST_BLINK_TIME = now
                    blink_todo = blink_todo - 1
                    LAST_SLEEP_TIME = now
        else:
            if now >= LAST_SLEEP_TIME + BLINK_PAUSE_DURATION:
                LAST_SLEEP_TIME = now
                blink_todo = BLINK_COUNT
                #print("Next blinking scheduled: ", blink_todo)
