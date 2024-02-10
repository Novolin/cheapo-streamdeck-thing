# External Libraries:
import asyncio
import board
import busio
import displayio
import adafruit_ssd1306
from digitalio import Direction, DigitalInOut, Pull
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import time
import scr

# Establish custom classes


class Stream:
    # basically the cathcall program class
    def __init__(self, display_obj):
        self.display = display_obj
        self.screen = scr.MainScreen(display_obj)
        self.running = False
        self.time = 0
        self.start_time = 0
        self.mute = False
        self.brb = False
        self.wait_for_response = False
        self.response_value = 0
        self.await_event = 0

    def tick(self):
        if self.running:
            self.time = self.start_time - time.time()

    def toggle_brb(self):
        for k in key_binds[2 + self.brb]:
            kbd.press(k)
        self.brb = not self.brb
        kbd.release_all()

    def toggle(self): #Start/Stop function
        if self.response_value == 1:
            self.running = not self.running
            for k in key_binds[0 + self.running]:
                kbd.press(k)
            self.response_value = 0
            self.wait_for_response = False
            kbd.release_all()

    def toggle_mute(self):
        for k in key_binds[4 + self.mute]:
            kbd.press(k)
        self.mute = not self.mute
        kbd.release_all()

    def do_response(self, response = -1): # handle responses from lcd commands
        if response == -1:
            response = self.response_value
        if response == 2:
            eventStack.append(self.await_event)
        elif response == 1:
            if self.brb:
                self.screen = scr.StreamPaused(self.display)
            elif self.running:
                self.screen = scr.StreamRunning(self.display, self)
            else:
                self.screen = scr.MainScreen(self.display)

        # return to null state
        self.await_event = 0
        self.wait_for_response = False
        self.response_value = 0

class LED:
    def __init__(self, pin):
        self.pin = DigitalInOut(pin)
        self.pin.direction = Direction.OUTPUT
    def set(self, value):
        self.pin.value = value

class InputKey:
    def __init__(self, key_pin, id):
        self.pin = DigitalInOut(key_pin)  # What pin is it connected to
        self.pin.direction = Direction.INPUT
        self.pin.pull = Pull.UP
        self.id = id  # What should we label it?


# Initialize hardware interfaces:
displayio.release_displays()
i2c = busio.I2C(board.GP1, board.GP0)
display = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
kbd = Keyboard(usb_hid.devices)

blink_state = False  # Global for if blinking lights should be lit or not.
eventStack = []  # List of events to fire
keys_pressed = []
display.text("LOADING...", 0, 20, 1, size=2)
display.show()
stream = Stream(display)

class KeyEvent:
    def __init__(self, eventID):
        self.eventID = eventID

    def fire(self):
        if self.eventID == 0:  # ui_left
            get_scr_response = stream.screen.left_action()
            if stream.wait_for_response:
                stream.do_response(get_scr_response)
        elif self.eventID == 1:  # ui_right
            get_scr_response = stream.screen.right_action()
            stream.response_value = get_scr_response
            if stream.wait_for_response:
                stream.do_response(get_scr_response)
        elif self.eventID == 2:  # start/stop
            if not stream.wait_for_response:
                if stream.running:
                    stream.await_event = StreamEvent(0)
                    
                else:
                    stream.await_event = StreamEvent(0)
                    eventStack.append(ScreenEvent("Start"))
                stream.wait_for_response = True
        elif self.eventID == 3:  # mute
            stream.toggle_mute()
        elif self.eventID == 4:  # brb
            if not stream.wait_for_response:
                if stream.brb:
                    stream.await_event = StreamEvent(1)
                    eventStack.append(ScreenEvent("resume"))
                    stream.wait_for_response = True
                else:
                    stream.toggle_brb()

class ScreenEvent:
    def __init__(self, action_id):
        self.action_id = action_id

    def fire(self):
        if type(self.action_id) == str:  # begin countdown timer
           stream.wait_for_response = True
           stream.screen = scr.CountScreen(display, self.action_id)
           stream.screen.start_countdown()
        elif self.action_id == 0:  # Draw the screen base:
            stream.screen.draw_screen_template()

class StreamEvent:
    # Polls if the stream is awaiting a response, processes event needed
    
    def __init__(self, action_id) -> None:
        self.action_id = action_id
    def fire(self):
        if self.action_id == 0: # Start
            stream.toggle()
        elif self.action_id == 1: # brb
            stream.toggle_brb()


# Poll keys for status
async def await_key_press():
    while True:
        # Poll the keys, see if they're pressed!
        for k in key_list:
            if not k.pin.value:
                # It's pressed! Make sure it's not being held:
                if (
                    k.id not in keys_pressed
                ):  # If it's not, flag it as being pressed, and set an event.
                    keys_pressed.append(k.id)
                    eventStack.append(KeyEvent(k.id))
                    if k.id == 2:
                        stream.screen.blink_left = True
                    elif k.id == 3:
                        stream.screen.blink_right = True
            else:  # If it's not pressed, drop it from the pressed list
                if k.id in keys_pressed:
                    keys_pressed.remove(k.id)
                    if k.id == 2:
                        stream.screen.blink_left = False
                    elif k.id == 3:
                        stream.screen.blink_right = False
        await asyncio.sleep_ms(50)  # fire every 50ms for software anti bounce

# Handle event Queue
async def process_events():
    # Async function to process any awaiting events
    global eventStack
    while True:
        while len(eventStack) > 0:
            next_event = eventStack.pop()
            next_event.fire()
        await asyncio.sleep(5)

# blink the lights. 
async def blink():
    # blink lights
    global blink_state
    global screen # let me access the screen from here
    while True:
        blink_state = not blink_state
 
        # handle mute/brb lights. these are very quick so don't bother with anything else.
        if stream.mute:
            light_list[1].set(blink_state)
        else: 
            light_list[1].set(False)
        if stream.brb:
            light_list[0].set(blink_state)
        else:
            light_list[0].set(False)
        
        await asyncio.sleep_ms(500)  # 1 second blink period

# refresh screen if needed
async def refresh_screen():
    stream.screen.draw_screen_template()
    while True:
        if stream.screen.needs_refresh:
            stream.screen.draw()
            stream.screen.needs_refresh = False
        await asyncio.sleep_ms(50)


async def check_stream_status():
    # checks if the stream is running, or has any tasks/state changes
    while True:
        await asyncio.sleep_ms(100)

async def main():
    while True:
        key_task = asyncio.create_task(await_key_press())
        blink_task = asyncio.create_task(blink())
        screen_task = asyncio.create_task(refresh_screen())
        event_task = asyncio.create_task(process_events())
        await asyncio.gather(event_task, blink_task, key_task, screen_task)


light_list = [  # List of LEDs
    LED(board.GP28),  # the silkscreen on the board is wrong, its 28, not 29
    LED(board.GP15) # mute light
]
key_list = [  # List of input keys
    InputKey(board.GP8, 0),  # top right, brb
    InputKey(board.GP9, 1),  # top left, mute
    InputKey(board.GP13, 2),  # bottom left, left ui
    InputKey(board.GP27, 3),  # bottom middle, right ui
    InputKey(board.GP5, 4)  # bottom right, start/stop
]
key_binds = [ 
    [Keycode.RIGHT_SHIFT, Keycode.A],  # Start stream
    [Keycode.RIGHT_SHIFT, Keycode.B],  # Stream End
    [Keycode.RIGHT_SHIFT, Keycode.C],  # BRB start
    [Keycode.RIGHT_SHIFT, Keycode.D],  # BRB End
    [Keycode.RIGHT_SHIFT, Keycode.E],  # Mute start
    [Keycode.RIGHT_SHIFT, Keycode.F]
    ]  # List of shortcut key combos

key_binds_REAL = [  # List of shortcut key combos
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F9],  # Start stream
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F10],  # Stream End
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F1],  # BRB start
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F2],  # BRB End
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F11],  # Mute start
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F12]  # Mute end
]

asyncio.run(main())