### Circuit Bluefruit Express CoronAlert Scanner
### Listen to Contact Tracing message and display the number phones nearby

### Copy this file to CPB board as code.py

### Tested with Circuit Playground Bluefruit:
### Adafruit CircuitPython 6.0.0-alpha.2 on 2020-07-23; Adafruit Circuit Playground Bluefruit with nRF52840

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
_button_b = digitalio.DigitalInOut(board.BUTTON_B)
_button_b.switch_to_input(pull=digitalio.Pull.DOWN)
button_left = lambda: _button_b.value
button_right = lambda: _button_a.value

BRIGHTNESS = 0.3
BLUE = (0, 0, 255)
OFF = (0, 0, 0)
strip = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=BRIGHTNESS)
strip.fill(BLUE)
time.sleep(1)
strip.fill(OFF)

rows = 10

debug = 1

def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)

screen_update_ns = 250 * 1000 * 1000
last_seen_update_ns = time.monotonic_ns()

stale_time_ns = 65 * 1000 * 1000 * 1000
scan_time_s = 10

ble = BLERadio()
ble.name = "CPB"

count = 1

complete_names_count = {}
addresses_count = {}
oui_count = {}

### An array of timestamp and advertisement by key (addr)
last_ad_by_key = {}

c_name_by_addr = {}

def remove_old(ad_by_key, expire_time_ns):
    """Delete any entry in the ad_by_key dict with a timestamp older than expire_time_ns."""
    ### the list() is needed to make a real list from the iterator 
    ### which allows modification of the dict inside the loop
    for key, value in list(ad_by_key.items()):
        if value[1] < expire_time_ns:
            del ad_by_key[key]


### TODO: arg list is getting big here
def gimme_color(disp, rows_g):
    
    return ( (255, 0, 0) )


def update_screen(rows_n,
                    ad_by_key,
                    then_ns,
                    tot_mac,
                    tot_oui,
                    tot_names,
                    *,
                    mem_free=None):
    """Update the screen with the entries with highest RSSI, recenctly seen.
       The text colour is used to indicate how recent.
       """

    if mem_free is None:
        summary_text = "MACs:{:<4d}  OUIs:{:<4d}  Names:{:<4d}".format(tot_mac,
                                                                       tot_oui,
                                                                       tot_names)
    else:
        summary_text = "MACs:{:<4d}  OUIs:{:<4d}  Names:{:<4d} M:{:<3d}".format(tot_mac,
                                                                                tot_oui,
                                                                                tot_names,
                                                                                round(mem_free/1024.0))
    d_print(3,
            summary_text)


    ### Sort by the RSSI field, then the time field
    sorted_data = sorted(ad_by_key.items(),
                         key=lambda item: (item[1][2], item[1][1]),
                         reverse=True)

    ### Add the top N rows to to the screen
    ### the key is the mac address as text without any colons
    idx = 0
    for key, value in sorted_data[:rows_n]:
        ad, ad_time_ns, rssi = value
        ### Add the colon sepators to the string version of the MAC address
        masked_mac = key
        mac_text = ":".join([masked_mac[off:off+2] for off in range(0, len(masked_mac), 2)])
        name = c_name_by_addr.get(key)
        if name is None:
            name = "?"
        ### Must be careful not to exceed the fixed max_glyphs field size here (40)
        ### This should be from 0 to about 65s-75s
        age = 170 - (then_ns - ad_time_ns) / stale_time_ns * 170
        brightness = min(max(round(85 + age * 2.4), 0), 255)
        d_print(6, "Set ", idx, " to brightness: ", brightness)
        strip[idx]=(0,0,brightness)
        idx += 1

    #### Blank out any rows not populated with data
    if idx < rows_n:
        for _ in range(rows_n - idx):
            strip[_ + idx]=(0, 0, 0)
            d_print(6, "Set ", _ + idx, " to off.")


while True:
    d_print(2, "Loop", count)
    for ad in ble.start_scan(minimum_rssi=-127, timeout=scan_time_s):
        now_ns = time.monotonic_ns()

        if 3 in ad.data_dict:
            if ad.data_dict[3] == b'o\xfd':

                ##addr_b = ad.address.address_bytes
                c_name = ad.complete_name
                addr_text = "".join(["{:02x}".format(b) for b in reversed(ad.address.address_bytes)])

                last_ad_by_key[addr_text] = (ad, now_ns, ad.rssi)

                try:
                    addresses_count[addr_text] += 1
                except KeyError:
                    addresses_count[addr_text] = 1

                oui = addr_text[:6]
                try:
                    oui_count[oui] += 1
                except KeyError:
                    oui_count[oui] = 1
    
                if c_name is not None:
                    c_name_by_addr[addr_text] = c_name
                    try:
                        complete_names_count[c_name] += 1
                    except KeyError:
                        complete_names_count[c_name] = 1      

        if button_right():
            debug_mem_free = gc.mem_free()
            print("Memfree: ", debug_mem_free)
            while button_right():
                pass

        if button_left():
            print(
                "MACS", len(addresses_count),
                "OUI", len(oui_count),
                "NAMES", len(complete_names_count))
            while button_left():
                pass

        if now_ns - last_seen_update_ns > screen_update_ns:
            gc.collect()
            mem_free = gc.mem_free()

            update_screen(rows,
                        last_ad_by_key,
                        now_ns,
                        len(addresses_count),
                        len(oui_count),
                        len(complete_names_count),
                        mem_free=mem_free)

            last_seen_update_ns = now_ns

        d_print(4,
                ad.address, ad.rssi, ad.scan_response,
                ad.tx_power, ad.complete_name, ad.short_name)

    remove_old(last_ad_by_key, time.monotonic_ns() - stale_time_ns)

    d_print(2,
            "MACS", len(addresses_count),
            "OUI", len(oui_count),
            "NAMES", len(complete_names_count))

    count += 1
