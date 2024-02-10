# rewritten with a better understanding of asyncio
# External Libraries:
from math import ceil
import asyncio
import board
import busio
import displayio
import adafruit_ssd1306
from adafruit_framebuf import FrameBuffer
from digitalio import Direction, DigitalInOut, Pull
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import time
import adafruit_imageload
import os

#prepare hardware interfaces first:
displayio.release_displays()
i2c = busio.I2C(board.GP1, board.GP0)
kbd = Keyboard(usb_hid.devices)

# Image file classes
class Image:
    # Bitmap image that can be passed to the screen display stuff
    def __init__(self, file, pos_x, pos_y, size_x, size_y):
        # It's only a black/white bmp so whatevs.
        self.bitmap = adafruit_imageload.load(file)[0]
        self.size_x = size_x
        self.size_y = size_y
        self.pos_x = pos_x
        self.pos_y = pos_y
    def draw(self, buff):
        # Draws the image to a given position in the framebuffer
        for x in range(self.size_x):
            for y in range(self.size_y):
                buff.pixel(x + self.pos_x, y + self.pos_y , self.bitmap[x + (self.size_x * y)])

class Anim:
    def __init__(self, file_list, pos_x = 2, pos_y = 2, size_x = 124, size_y = 44, loops = False):
        self.loops = loops
        self.current_frame = 0
        self.frames = []
        self.size_x = size_x
        self.size_y = size_y
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.run = True
        for f in file_list:
            self.frames.append(adafruit_imageload.load(f))
    def draw(self, buff):
        # Draws the current frame to a given position in the framebufferm increments the counter
        for x in range(self.size_x):
            for y in range(self.size_y):
                buff.pixel(x + self.pos_x, y + self.pos_y , self.bitmap[x + (self.size_x * y)])
        self.current_frame += 1
        if self.current_frame >= len(self.frames):
            self.current_frame = 0 
        display.need_refresh = True
    def draw_next(self, buff):
        if self.run:
            self.draw(buff)
            if self.current_frame == 0:
                self.loops -= 1
            if self.loops < 0: # if we're still waiting to loop, we can wait for the given frame timer
                self.run = False # end looping
        return self.run

# I/O classes:
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
        self.held = False
    def read(self):
        return self.pin.value

class Display:
    def __init__(self):
        self.screen = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
        self.left_key = DispButton("Left", "LEFT")
        self.right_key = DispButton("Right", "RIGHT")
        self.need_refresh = True
        buff = bytearray(1024)
        self.framebuffer = FrameBuffer(buff, 128,64)
        self.countdown = False
        self.animation = False
        self.bg = Image("bg.bmp", 0,0,128,64)


        # display a loading screen until we push something else:
        self.screen.text("LOADING", 10, 20,1,size = 3)
    
    def begin(self): # draw the bg on its own
        self.framebuffer.fill_rect(128,64,0)
        self.framebuffer.image(self.bg)
        self.need_refresh = True

    def draw_buffer(self):
        # Pushes framebuffer to the screen.
        self.screen.write_framebuf(self.framebuffer)
        self.need_refresh = False
    
    def blank_buffer(self): # blank the main display area
        self.framebuffer.fill_rect(1,2,126,47)
        
    def blit_img(self, image):
        image.draw(self.framebuffer)

    async def disp_ani(self, ftime):
        while self.animation:
            keep_going = self.animation.draw_next(self.framebuffer)
            if keep_going:
                await asyncio.sleep_ms(ftime)
            else:
                self.animation = False

# the button that gets displayed on the screen
class DispButton:
    def __init__(self, text, position):
        self.text = text[0:9]
        if position == "LEFT":
            self.pos_x = 2
        else:
            self.pos_x = 65
        self.pos_y = 53
        self.is_active = False
    
    def draw(self,buff, showbg = False):
        buff.fill_rect(self.pos_x, self.pos_y, 60, 11, showbg)
        center_x = self.pos_x + 60 -  60//len(self.text)
        buff.text(self.text, center_x, self.pos_y, not self.showbg)

# Object to handle countdown timers
class Timer:
    def __init__(self, display, timer_func, t = 10):
        self.time_target = time.monotonic() + t
        self.display = display
        self.timer_func = timer_func # what the non-timeout result is
        self.result = "AWAIT"
    
    async def tick(self):
        time_remaining = self.time_target - time.monotonic()
        if time_remaining > 0:
            # we're awaiting the countdown, write a progress bar here
            # throw that bitch right to the screen
            display.screen.rect(2,28,124,16,1)
            bar_len = 124 - round(124 * time_remaining)
            display.screen.fill_rect(2,28,bar_len,16,1)
            if display.left_key.is_active:
                self.result = False
            elif display.right_key.is_active:
                self.result = self.timer_func
            else:
                self.result = "AWAIT"
        else:
            self.result =  False # default to the left button if there's no input.

# Stream data:
class Stream:
    def __init__(self):
        # Status:
        self.running = False
        self.brb = False
        self.mute = False
        self.start_time = 0 # When did the stream begin.

    def begin_stream(self):
        self.running = True
        self.start_time = time.monotonic()
        # set the framebuffer to be the stream data page
        display.need_refresh = True

    async def tick(self):
        # tick the stream timer!
        display.blank_buffer()
        # now write the new data to the screen
        display.need_refresh = True # flag for a redraw

# Begin initializing objects:
display = Display() # do this bad boy first because it has a loading screen
stream = Stream()

light_list = [  # List of LEDs
    LED(board.GP28),  # the silkscreen on the board is wrong, its 28, not 29
    LED(board.GP15) # mute light
]

key_list = [  # List of input keys
    InputKey(board.GP8, "BRB"),  # top right, brb
    InputKey(board.GP9, "MUTE"),  # top left, mute
    InputKey(board.GP13, "UI_LEFT"),  # bottom left, left ui
    InputKey(board.GP27, "UI_RIGHT"),  # bottom middle, right ui
    InputKey(board.GP5, "START_STOP")  # bottom right, start/stop
]

key_binds = { # This is a testing version, so we can easily read what comes out
    "START": [Keycode.RIGHT_SHIFT, Keycode.ONE],  # Start stream
    "END": [Keycode.RIGHT_SHIFT, Keycode.TWO],  # Stream End
    "PAUSE": [Keycode.RIGHT_SHIFT, Keycode.THREE],  # BRB start
    "RESUME": [Keycode.RIGHT_SHIFT, Keycode.FOUR],  # BRB End
    "MUTE": [Keycode.RIGHT_SHIFT, Keycode.FIVE],  # Mute start
    "UNMUTE": [Keycode.RIGHT_SHIFT, Keycode.SIX]
    }

key_binds_REAL = {  # List of shortcut key combos
    "START": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F9],  # Start stream
    "END": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F10],  # Stream End
    "PAUSE": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F1],  # BRB start
    "RESUME": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F2],  # BRB End
    "MUTE": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F11],  # Mute start
    "UNMUTE": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F12]  # Mute end
}

# preload the images we will use later:
idle_bg = Image("img/idle.bmp", 2, 2, 124, 44)

stream_bg = Image("img/live.bmp", 2,2,124, 25)

boot_anim = Anim([
    "anim/start0.bmp",
    "anim/start1.bmp",
    "anim/start2.bmp",
    "anim/start3.bmp",
    "anim/start4.bmp",
    "anim/start5.bmp",
    "anim/start6.bmp",
    "anim/start7.bmp",
    "anim/start8.bmp",
    "anim/start9.bmp",
    "anim/start10.bmp",
    "anim/start11.bmp",
    "anim/start12.bmp",
    ])
brb_anim = Anim([
    "anim/brb/0.bmp",
    "anim/brb/1.bmp",
    "anim/brb/2.bmp",
    "anim/brb/3.bmp"
    ], loops = 99999)
# Establish monitor function:
async def main():
    while True:
        stack = []
        if int(time.monotonic()) % 2 == 0: # every other second, blink the leds if active
            light_list[0].set(stream.brb)
            light_list[1].set(stream.mute)
        
        stack.append(asyncio.create_task(poll_inputs()))
        stack.append(asyncio.create_task(refresh_screen(display)))
        if stream.running:
            stack.append(asyncio.create_task(stream.tick()))
        if display.countdown:
            stack.append(asyncio.create_task(display.countdown.tick()))
        elif display.animation: # only play animations if there's no countdown
            stack.append(asyncio.create_task(display.disp_ani()))
        await asyncio.gather(stack)
        if display.countdown:
            process_timer_result(display.countdown.result)

# Establish timing-based functions:
async def refresh_screen(screen):
    while True:
        if display.needs_refresh:
            display.draw_buffer()

        await asyncio.sleep_ms(50)

async def poll_inputs():
    while True:
        for input in key_list:
            if input.read():
                if not input.held: # if it's only now being held:
                    input.held = True
                    execute_input(input.id)
                else:
                    input.held += 1
                    if input.held > 3:
                        input.held == 0 # require a few cycles to clear a pressed key.
        await asyncio.sleep_ms(50)

# Input-related
def execute_input(key): # Executes the command assigned to a key, or calls the subroutine it requires
    if key == "MUTE": # We let mute run whenever, no confirmation needed.
        stream.mute = not stream.mute
        if stream.mute: # we've inverted it, so we do the opposite
            send_keypress("MUTE")
        else: 
            send_keypress("UNMUTE")
    elif key == "LEFT": #L/R commands are handled elsewhere, so flag them to run
        display.left_key.is_active = True 
    elif key == "RIGHT":
        display.right_key.is_active = True
    elif key == "BRB": # we can pause the stream with one keypress, but to resume call for a confirmation
        if stream.brb:
            prepare_timer("RESUME")
        else:
            stream.brb = True
            send_keypress(2)
    elif key == "START_STOP":
        if stream.running:
            prepare_timer("START")
        else:
            prepare_timer("STOP")

def send_keypress(id): # actually send the keypress to the computer
    for k in key_binds[id]:
        kbd.press(k)
    kbd.release_all()

# Timer-related

def prepare_timer(timer_type):
    display.countdown = Timer(display, timer_type)
    display.left_key = DispButton("Cancel", "LEFT")
    display.right_key = DispButton("Confirm", "RIGHT")
    display.left_key.draw(display.framebuffer, True)
    display.right_key.draw(display.framebuffer, True)
    display.blank_buffer()
    msg_offset = 128//(7 + len(timer_type))
    display.framebuffer.text("Really " + timer_type.lower() + "?", msg_offset, 10)
    display.need_refresh = True   

def process_timer_result(result):
    if result:
        if result != "AWAIT": # If we're not being told to wait
            send_keypress(result)
            if result == "START":
                print("Start the stream")
            elif result == "END":
                print("End The Stream")
            elif result == "RESUME":
                print("Return to the stream page")
    else:
        display.countdown = False # kill the display countdown
        if stream.brb:
            print("return to brb screen")
        elif stream.running:
            print("return to the stream clock")
        else:
            print("Return to the idle screen")    

# Initialize the display:
display.begin()
display.animation = boot_anim
# Run that bad boy
asyncio.run(main())