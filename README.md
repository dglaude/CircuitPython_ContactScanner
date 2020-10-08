# CircuitPython_ContactScanner
Detecting Contract Tracing BLE advertisement with CircuitPython

## cpb_corona.py : Simple version NeoPixel for Circuit Playground Bluefruit

See also: https://twitter.com/DavidGlaude/status/1311791062445371398?s=20

## clue_cpb_scanner.py : Graphical version working on Circuit Playground Bluefruit and CLUE

See also: https://twitter.com/DavidGlaude/status/1224061386185154561?s=20



Credit for most of the code to @kevinjwalters: https://github.com/kevinjwalters/circuitpython-examples/blob/master/clue/clue-ble-scanner.py


## Using the Circuit Playground Bluefruit

Once started, the code is scanning for BLE advertisement.
When an advertising phone is detected, one LED is assign to the advertised address and a color is  displayed.

### Why this gadget

You can check how many phone around you have the app install, and engage the conversation on why contact tracing can help fight the virus.
It can be a bit creepy as you can see the invisible fact that someone installed or not the app on thier phone, and that's a personal decision.
So use wisely and don't put judgement if someone did not install the app.
This is just to start the conversation.

### Color code

The colour give information about the power level of the signal received:
* GREEN: We see a signal, but it is weak, there is a phone nearby but not too close
* RED: We see a signal, very strong (this is usefull to indentify what LED is your phone associated with)
* YELLOW: The signal power is in between GREEN and RED
* BLUE: We have not receive an advertisement from that address since at least 20 second
* OFF: No signal received since a long time, this LED is recycled for reuse by a another address

### Quirk on random address

Please notice that phone do not use their hardware MAC address and change every 10-15 minutes.
It is possible to make some guessing because one address is not in use just as a new one start to be used.
But when your phone change address, the associated LED will turn BLUE within 20 seconds, while another LED will be associated to the new address.

If a phone move away from your CPB, and then return closer, if it still has the same address, the BLUE LED will turn GREEN again at the same position.

By turning ON and OFF again the Bluetooth of your phone, you trigger and address change, using a new LED on the CPB.
You can use that trick to see the BLUE color or test the behaviour when a lot of phone are nearby.

### Experimenting

I tested with my CPB in "various places":
* In public transport just passing near people and all the LED start to be used, many turning BLUE as you walk away.
* In a theater, all the LED turned green and as spectator are static, it stay that way.
* At home, the LED show people in the room, it turn blue when someone change room.
* In the street, as you pass nearby someone, you can tell if they have the app installed or not, for a couple, you would see two new LED.
