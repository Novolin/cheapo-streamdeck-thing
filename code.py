# External Libraries:
import asyncio
import board
import busio
import displayio
import adafruit_ssd1306
from digitalio import Direction, DigitalInOut, Pull, DriveMode
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import time
import scr
# Initialize hardware interfaces:
displayio.release_displays()
i2c = busio.I2C(board.GP1, board.GP0)
display = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

kbd = Keyboard(usb_hid.devices)
blink_state = False # Global for if blinking lights should be lit or not.
eventStack = [] # List of events to fire
keys_pressed = []
display.text("LOADING...",0,20, 1, size = 2)
display.show()
active_screen = 0
next_screen = 0
screen_needs_refresh = True

class Stream:
    def __init__(self, last_time = 0):
        self.running = False
        self.time = False
        self.last_time = False
    def start_stream(self):
        self.running = True
        self.time = time.time()

    def pause_stream(self):
        if light_list[0].blink == False:
            light_list[0].blink = True
        if light_list[0].blink == True:
            light_list[0].blink = False

    def end_stream(self):
        self.running = True


class LED:
    def __init__(self, pin):
        self.pin = DigitalInOut(pin)
        self.pin.direction = Direction.OUTPUT
        self.blink = False

    def toggle(self):
        self.pin.value = not self.pin.value


    def set_state(self, state):
        self.pin.value = state

    def toggle_blink(self):
        self.blink = not self.blink
        self.pin.value = blink_state

class InputKey:
    def __init__(self, key_pin, scan_code, name, led = False, keyboard = kbd):
        self.pin = DigitalInOut(key_pin) # What pin is it connected to
        self.pin.direction = Direction.INPUT
        self.pin.pull = Pull.UP
        self.scan = scan_code # What keypress should it send?
        self.name = name # What should we label it?
        self.keyboard = keyboard # What keyboard object are we using, if any
        self.led = led
        self.key_mode = "key"

    def send_key_press(self):
        self.keyboard.send(self.scan)
        return self.name
    def execute_key_function(self):
        if self.key_mode:
            self.send_key_press()
        else:
            print(self.key_mode) # this is where we do any like screen shit

class Event:  # barebones event class
    def __init__(self):
        self.executed = False

    def fire(self):
        pass  # generic fire function


class KeyEvent(Event):
    def __init__(self, keyPress):
        super().__init__()
        self.keyPress = keyPress


    def fire(self):
        self.keyPress.send_key_press()

class LightEvent(Event):
    def __init__(self, light, eventType):
        super().__init__()
        self.light = light
        self.eventType = eventType

    async def fire(self):
        if self.eventType >= 2:
            self.light.toggle()
        else:
            self.light.set_state(self.eventType)

class ScreenEvent(Event):
    def __init__(self, action_id):
        self.action_id = action_id
        super().__init__()

    async def fire(self):
       if self.action_id == 0: # Draw the screen base:
        screen_list[active_screen].draw_screen_template()

async def await_key_press():
    while True:
        # Poll the keys, see if they're pressed!
        for k in key_list:
            if not k.pin.value:
                #It's pressed! Make sure it's not being held:
                if k.name not in keys_pressed: # If it's not, flag it as being pressed, and set an event.
                    keys_pressed.append(k.name)
                    eventStack.append(KeyEvent(k))
            else: # If it's not pressed, drop it from the pressed list
                if k.name in keys_pressed:
                    keys_pressed.remove(k.name)
        await asyncio.sleep_ms(50) # fire every 50ms for software anti bounce

async def process_events():
    # Async function to process any awaiting events
    global eventStack
    while True:
        while len(eventStack) > 0:
            eventStack[0].fire()
            eventStack.pop(0)
        await asyncio.sleep(0)

async def blink():
    global blink_state
    while True:
        blink_state = not blink_state
        for light in light_list:
            if light.blink:
                eventStack.append(LightEvent(light, blink_state))

        screen_list[active_screen].do_blink(blink_state)
        await asyncio.sleep_ms(500) # 1 second blink duration

async def process_screen_event():
    global active_screen
    global screen_needs_refresh
    while True:
        if next_screen != active_screen or screen_needs_refresh:
            active_screen = next_screen
            screen_list[active_screen].draw_screen_template()
            screen_list[active_screen].draw()
            screen_needs_refresh = False
        await asyncio.sleep_ms(100)

async def main():
    while True:
        key_task = asyncio.create_task(await_key_press())
        blink_task = asyncio.create_task(blink())
        screen_task = asyncio.create_task(process_screen_event())
        event_task = asyncio.create_task(process_events())
        await asyncio.gather(event_task, blink_task, key_task)

light_list = [ # List of LED objects
    LED(board.GP28), # the silkscreen on the board is wrong, its 28, not 29
    LED(board.GP15)
]
key_list = [ # List of input keys
    InputKey(board.GP27, Keycode.A, "k1", light_list[0]),
    InputKey(board.GP13, Keycode.B, "k2", light_list[1]),
    InputKey(board.GP8, Keycode.C, "k3"),
    InputKey(board.GP9, Keycode.D, "k4"),
    InputKey(board.GP5, Keycode.E, "k5"),
]
screen_list = [scr.ClockScreen(display),
    scr.Screen(display, "scr2", "1234567890"),
    scr.Screen(display, "Back", "Next")
]

asyncio.run(main())
