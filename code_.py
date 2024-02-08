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
    def __init__(self):
        self.running = False
        self.time = 0
        self.start_time = 0
        self.mute = True
        self.brb = False

    def tick(self):
        if self.running:
            self.time = self.start_time - time.time()

    def start_stream(self):
        global screen
        self.running = True
        self.start_time = time.time()
        eventStack.append(ScreenEvent(3))
        

    def toggle_brb(self):
        self.brb = not self.brb
        '''if not self.brb:
            self.brb = True
            for k in key_event_list[2]:
                kbd.press(k)
            kbd.release_all()'''

    def resume_stream(self):
        # Return from a BRB screen
        
        return

    def toggle(self):
        pass

    def toggle_mute(self):
        self.mute = not self.mute
            
        # send key signal


class LED:
    def __init__(self, pin):
        self.pin = DigitalInOut(pin)
        self.pin.direction = Direction.OUTPUT


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
current_stream = Stream()
screen = scr.MainScreen(display)

class KeyEvent:
    def __init__(self, eventID):
        self.eventID = eventID

    def fire(self):
        print("key: ", end = "")
        print(self.eventID)
        if self.eventID == 0:  # ui_left
            
            get_scr_response = screen.left_action()
            if type(get_scr_response) == int:
                eventStack.append(ScreenEvent(0))
            else:
                scr_response = get_scr_response
        elif self.eventID == 1:  # ui_right
            get_scr_response = screen.right_action()
            if type(get_scr_response) == int:
                eventStack.append(ScreenEvent("ass"))
            else:
                scr_response = get_scr_response
        elif self.eventID == 2:  # start/stop
            current_stream.toggle()
        elif self.eventID == 3:  # mute
            current_stream.toggle_mute()
        elif self.eventID == 4:  # brb
            current_stream.toggle_brb()

class ScreenEvent:
    def __init__(self, action_id):
        self.action_id = action_id

    def fire(self):
        global screen
        if self.action_id == 0:  # Draw the screen base:
            screen.draw_screen_template()
        elif self.action_id == 1:  # blink action
            screen.do_blink(blink_state)
        elif type(self.action_id) == str:  # begin countdown timer
           screen = scr.CountScreen(display, self.action_id)

class StreamEvent:
    # Event type for stream actions, e.g. pausing, etc.
    def __init__(self, action_id, stream_obj) -> None:
        self.action_id = action_id
        self.stream_obj = stream_obj
    def fire(self):
        if self.action_id == 0:
            self.stream_obj.toggle()
def send_key_combo(combo):
    for k in key_event_list[combo]:
        kbd.press(k)
    kbd.release_all()

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
            else:  # If it's not pressed, drop it from the pressed list
                if k.id in keys_pressed:
                    keys_pressed.remove(k.id)
        await asyncio.sleep_ms(50)  # fire every 50ms for software anti bounce


async def process_events():
    # Async function to process any awaiting events
    global eventStack
    while True:
        while len(eventStack) > 0:
            next_event = eventStack.pop()
            next_event.fire()
        await asyncio.sleep(0)

async def blink():
    # blink lights, also general timer stuff
    global blink_state
    while True:
        blink_state = not blink_state
        if blink_state:
            if current_stream.running:
                current_stream.tick()  # tick every other half second
        # handle mute/brb lights. these are very quick so don't bother with anything else.
        if current_stream.mute:
            light_list[0].value = blink_state
        if current_stream.brb:
            light_list[1].value = blink_state
        if (
            screen.blink_left
            or screen.blink_right
        ):
            eventStack.append(ScreenEvent(1))
        await asyncio.sleep_ms(500)  # 1 second blink period


async def refresh_screen():
    while True:
        if screen.needs_refresh:
            screen.draw_screen_template()
            screen.draw()
            screen.needs_refresh = False
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
    LED(board.GP15),
]
key_list = [  # List of input keys
    InputKey(board.GP8, 0),  # top right, brb
    InputKey(board.GP9, 1),  # top left, mute
    InputKey(board.GP13, 2),  # bottom left, left ui
    InputKey(board.GP27, 3),  # bottom middle, right ui
    InputKey(board.GP5, 4)  # bottom right, start/stop
]

key_event_list = [  # List of shortcut key combos
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F9],  # Start stream
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F10],  # Stream End
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F1],  # BRB start
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F2],  # BRB End
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F11],  # Mute start
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F12],  # Mute end
]

asyncio.run(main())
