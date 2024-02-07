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

#Establish custom classes

class Stream:
    def __init__(self, last_time = 0):
        self.running = False
        self.time = False
        self.start_time = 0
        self.last_time = False
        self.mute = False
        self.brb = False

    def tick(self):
        if self.running:
            self.time = self.start_time - time.time()

    def start_stream(self):
        self.running = True
        self.start_time = time.time()


    def pause_stream(self):
        # put the screen on BRB
        self.brb = True
        if light_list[0].blink == False:
            light_list[0].blink = True
        if light_list[0].blink == True:
            light_list[0].blink = False
    def resume_stream(self):
        # Return from a BRB screen
        self.brb = False
        # send keypress

    def end_stream(self):
        self.running = True
    def mute_stream(self):
        self.mute = False
        #send key signal

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
    def __init__(self, key_pin, id):
        self.pin = DigitalInOut(key_pin) # What pin is it connected to
        self.pin.direction = Direction.INPUT
        self.pin.pull = Pull.UP
        self.id = id # What should we label it?


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
last_screen = 0
screen_needs_refresh = True # should we write the complete image buffer
current_stream = Stream()



class KeyEvent:
    def __init__(self, eventID):
        self.eventID = eventID

    async def fire(self):
        if self.eventID == 0: #ui_left
            print("A")
        elif self.eventID == 1: #ui_right
            print("B")
        elif self.eventID == 2: #start/stop
            print("C")
        elif self.eventID == 3: #mute
            print("D")
        elif self.eventID == 4: #brb
            print("E")


class LightEvent:
    def __init__(self, light, eventType):
        self.light = light
        self.eventType = eventType

    async def fire(self):
        if self.eventType >= 2:
            self.light.toggle()
        else:
            self.light.set_state(self.eventType)

class ScreenEvent:
    def __init__(self, action_id):
        self.action_id = action_id

    async def fire(self):
        if self.action_id == 0: # Draw the screen base:
            screen_list[active_screen].draw_screen_template()
        elif self.action_id == 1: # blink action
            screen_list[active_screen].do_blink(blink_state)
        elif self.action_id == 2: # left button action
            get_scr_response = screen_list[active_screen].left_action()
            if type(get_scr_response) == int:
                active_screen += get_scr_response
        elif self.action_id == 3: #right button action
            get_scr_response = screen_list[active_screen].right_action()
            if type(get_scr_response) == int:
                active_screen += get_scr_response
        elif type(self.action_id) == str: # begin countdown timer
            screen_list.append(scr.CountScreen(self.action_id))
            active_screen = -1
            screen_list[active_screen].draw_screen_template()
            screen_list[active_screen].start_countdown()



async def await_key_press():
    while True:
        # Poll the keys, see if they're pressed!
        for k in key_list:
            if not k.pin.value:
                #It's pressed! Make sure it's not being held:
                if k.id not in keys_pressed: # If it's not, flag it as being pressed, and set an event.
                    keys_pressed.append(k.id)
                    eventStack.append(KeyEvent(k.id))
            else: # If it's not pressed, drop it from the pressed list
                if k.id in keys_pressed:
                    keys_pressed.remove(k.id)
        await asyncio.sleep_ms(50) # fire every 50ms for software anti bounce

async def process_events():
    # Async function to process any awaiting events
    global eventStack
    while True:
        while len(eventStack) > 0:
            eventStack.pop().fire()
        await asyncio.sleep(0)

async def blink():
    global blink_state
    while True:
        blink_state = not blink_state
        if blink_state:
            if current_stream.running:
                current_stream.tick() # tick every other half second
            if active_screen < 0:
                if screen_list[active_screen].increment_count():
                    active_screen = last_screen
                    screen_list.pop() # remove the countdown
                    screen_list[active_screen].draw()
        for light in light_list:
            if light.blink:
                eventStack.append(LightEvent(light, blink_state))
        if screen_list[active_screen].blink_left or screen_list[active_screen].blink_right:
            eventStack.append(ScreenEvent(1))
        await asyncio.sleep_ms(500) # 1 second blink period
      
async def refresh_screen():
    global active_screen
    global screen_needs_refresh
    while True:
        if screen_needs_refresh:
            active_screen = next_screen
            screen_list[active_screen].draw_screen_template()
            screen_list[active_screen].draw()
            screen_needs_refresh = False
        await asyncio.sleep_ms(100)

async def main():
    while True:
        key_task = asyncio.create_task(await_key_press())
        blink_task = asyncio.create_task(blink())
        screen_task = asyncio.create_task(refresh_screen())
        event_task = asyncio.create_task(process_events())
        await asyncio.gather(event_task, blink_task, key_task, screen_task)

light_list = [ # List of LEDs
    LED(board.GP28), # the silkscreen on the board is wrong, its 28, not 29
    LED(board.GP15)
]
key_list = [ # List of input keys
    InputKey(board.GP27, 0), # bottom left, left ui
    InputKey(board.GP13, 1), # bottom middle, right ui
    InputKey(board.GP8, 2), # bottom right, start/stop
    InputKey(board.GP9, 3), # top left, mute
    InputKey(board.GP5, 4), # top right, brb
]

event_list = [ # List of shortcut key combos
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F9], # Start stream
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F10], # Stream End
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F1], # BRB start
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F2], #BRB End
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F11], # Mute start
    [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F12] # Mute end
]
screen_list = [ # The screens that may be displayed.
    scr.MainScreen(display),
    scr.StreamRunning(display, current_stream)

]

asyncio.run(main())
