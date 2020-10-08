# CircuitPython_ContactScanner
Detecting Contract Tracing BLE advertisement with CircuitPython

## cpb_corona.py : Simple version NeoPixel for Circuit Playground Bluefruit

See also: https://twitter.com/DavidGlaude/status/1311791062445371398?s=20

## clue_cpb_scanner.py : Graphical version working on Circuit Playground Bluefruit and CLUE

See also: https://twitter.com/DavidGlaude/status/1224061386185154561?s=20



Credit for most of the code to @kevinjwalters: https://github.com/kevinjwalters/circuitpython-examples/blob/master/clue/clue-ble-scanner.py


## How to use the Circuit Playground Bluefruit

Once started, the code is scanning for BLE advertisement.

When it detect a phone advertising, it assign one of the LED to the address advertised.
The colour give information about the power level of the signal received:
* GREEN: We see a signal, but it is weak, there is a phone nearby but not too close
* RED: We see a signal, very strong (this is usefull to indentify what LED is your phone associated with)
* YELLOW: The signal power is in between GREEN and RED
* BLUE: We have not receive an advertisement from that address since at least 20 second
* OFF: No signal received since a long time, this LED is recycled for reuse by a another address

Please notice that phone do not use their hardware MAC address and change every 10-15 minutes.
It is possible to make some guessing because one address is not in use just as a new one start to be used.
But when your phone change address, the associated LED will turn BLUE within 20 seconds, while another LED will be associated to the new address.

But if a phone move away from your CPB, and then return closer, if it still has the same address, the BLUE LED will turn GREEN again at the same position.

