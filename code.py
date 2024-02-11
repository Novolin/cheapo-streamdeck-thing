###################
# BUTTON BOX CODE #
#  WRITTEN FOR:   #
# *~*CHRISTINA*~* #
#      V1.0       #
###################
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
import adafruit_imageload


# prepare hardware interfaces first:
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
                buff.pixel(
                    x + self.pos_x, y + self.pos_y, self.bitmap[x + (self.size_x * y)]
                )


class Anim:
    def __init__(self, file_list, pos_x=2, pos_y=2, size_x=124, size_y=44, loops=False):
        self.loops = loops
        self.current_frame = 0
        self.frames = []
        self.size_x = size_x
        self.size_y = size_y
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.run = True
        for f in file_list:
            self.frames.append(adafruit_imageload.load(f)[0])

    def draw(self, buff):
        # Draws the current frame to a given position in the framebuffer
        # then increments the counter
        for x in range(self.size_x):
            for y in range(self.size_y):
                buff.pixel(
                    x + self.pos_x,
                    y + self.pos_y,
                    self.frames[self.current_frame][x + (self.size_x * y)],
                )
        self.current_frame += 1
        if self.current_frame >= len(self.frames):
            self.current_frame = -1
        display.need_refresh = True

    def draw_next(self, buff):
        self.draw(buff)
        if self.current_frame == -1:
            self.loops -= 1
            self.current_frame = 0
        if self.loops < 0:
            self.run = False  # end looping


# I/O classes:
class LED:
    def __init__(self, pin):
        self.pin = DigitalInOut(pin)
        self.pin.direction = Direction.OUTPUT

    def set(self, value):
        self.pin.value = value


class InputKey:
    def __init__(self, key_pin, k_id):
        self.pin = DigitalInOut(key_pin)  # What pin is it connected to
        self.pin.direction = Direction.INPUT
        self.pin.pull = Pull.UP
        self.id = k_id  # What should we label it?
        self.held = False

    def read(self):
        return not self.pin.value


class Display:
    def __init__(self):
        self.screen = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
        self.left_key = DispButton("Left", "LEFT")
        self.right_key = DispButton("Right", "RIGHT")
        self.needs_refresh = True
        self.countdown = False
        self.animation = False
        self.bg = Image("bg.bmp", 0, 0, 128, 64)  # main bg

        # display a loading screen for now:
        self.blit_img(self.bg)
        self.blit_img(Image("anim/boot0.bmp", 2, 2, 124, 44))
        self.screen.show()
        # preload images
        self.idle_bg = Image("img/idle.bmp", 2, 2, 124, 44)
        self.stream_bg = Image("img/live.bmp", 2, 2, 124, 25)

    def draw_buffer(self):
        # refreshes the screen.
        self.screen.show()
        self.need_refresh = False

    def blank_buffer(self):  # blank the main display area
        self.screen.fill_rect(1, 2, 126, 47, 0)

    def blit_img(self, image):
        image.draw(self.screen)

    def disp_ani(self):
        if self.animation.run:
            self.animation.draw_next(self.screen)

    def show_page(self, page):
        self.left_key = DispButton(" ", "LEFT")
        self.right_key = DispButton(" ", "RIGHT")
        self.animation = False  # instantly kill any animation
        if page == "IDLE":
            self.blank_buffer()
            self.blit_img(self.idle_bg)
        elif page == "RUN":
            self.blank_buffer()
            self.blit_img(self.stream_bg)
        elif page == "BRB":
            self.blank_buffer()
            self.animation = brb_anim
        self.left_key.draw(self.screen)
        self.right_key.draw(self.screen)
        self.need_refresh = True


# the button that gets displayed on the screen
class DispButton:
    def __init__(self, text, position):
        self.text = text[0:9]
        if position == "LEFT":
            self.pos_x = 2
        else:
            self.pos_x = 66
        self.pos_y = 53
        self.is_active = False

    def draw(self, buff, showbg=False):

        buff.fill_rect(self.pos_x, self.pos_y-2, (61 - self.pos_x //50), 11, showbg) #do a hack because it's a little uneven
        center_x = self.pos_x + 60 // len(self.text)
        buff.text(self.text, center_x, self.pos_y, not showbg)


# Object to handle countdown timers
class Timer:
    def __init__(self, display, timer_func, t=10):
        self.time_target = time.monotonic() + t
        self.display = display
        self.timer_func = timer_func  # what the non-timeout result is
        self.act = False
        display.animation = False  # kill any running animation

    def tick(self):
        time_remaining = int(self.time_target - time.monotonic())
        if time_remaining > 0:
            # we're awaiting the countdown, write a progress bar here
            # throw that bitch right to the screen
            display.screen.rect(2, 29, 122, 16, 1)
            bar_len = 12 * (10 - time_remaining)
            display.screen.fill_rect(2, 30, bar_len, 14, 1)
            if self.act == "CANCEL":
                result = False
            elif self.act == "CONFIRM":
                result = self.timer_func
            else:
                result = "AWAIT"
        else:
            result = False  # default to the left button if there's no input.
        return result


# Stream data:
class Stream:
    def __init__(self, display):
        # Status:
        self.running = False
        self.brb = False
        self.mute = False
        self.start_time = 0  # When did the stream begin.
        self.display = display
        self.last_tick = time.monotonic()

    def begin_stream(self):
        self.running = True
        self.start_time = time.monotonic()
        self.display.show_page("RUN")

    def end_stream(self):
        self.running = False
        self.brb = False
        self.display.show_page("IDLE")
    def pause(self):
        self.brb = True
        send_keypress("PAUSE")
        self.display.animation = brb_anim
    def resume(self):
        self.brb = False
        self.display.show_page("RUN")

    def tick(self):
        if time.monotonic() > self.last_tick + 1:
            self.last_tick += 1
            if self.running:
                stream_duration = int(time.monotonic() - self.start_time)
                if not self.brb and not self.display.countdown:
                    time_str = time_to_str(stream_duration)
                    self.display.screen.fill_rect(2, 28, 124, 16, 0)  # cover our sins
                    self.display.screen.text(time_str, 10, 28, 1, size=2)
                    self.display.need_refresh = True  # flag for a redraw

# Begin initializing objects:
display = Display()  # do this bad boy first because it has a loading screen
stream = Stream(display)

light_list = [  # List of LEDs
    LED(board.GP28),  # the silkscreen on the board is wrong, its 28, not 29
    LED(board.GP15),  # mute light
]

key_list = [  # List of input keys
    InputKey(board.GP8, "UI_LEFT"),
    InputKey(board.GP9, "UI_RIGHT"),
    InputKey(board.GP13, "BRB"),
    InputKey(board.GP27, "MUTE"),
    InputKey(board.GP5, "START_STOP"),
]
'''
key_binds = {  # This is a testing version, so we can easily read what comes out
    "START": [Keycode.RIGHT_SHIFT, Keycode.ONE],  # Start stream
    "STOP": [Keycode.RIGHT_SHIFT, Keycode.TWO],  # Stream End
    "PAUSE": [Keycode.RIGHT_SHIFT, Keycode.THREE],  # BRB start
    "RESUME": [Keycode.RIGHT_SHIFT, Keycode.FOUR],  # BRB End
    "MUTE": [Keycode.RIGHT_SHIFT, Keycode.FIVE],  # Mute start
    "UNMUTE": [Keycode.RIGHT_SHIFT, Keycode.SIX],
}'''

key_binds = {  # List of shortcut key combos
    "START": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F9],  # Start stream
    "STOP": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F10],  # Stream End
    "PAUSE": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F1],  # BRB start
    "RESUME": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F2],  # BRB End
    "MUTE": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F11],  # Mute start
    "UNMUTE": [Keycode.RIGHT_SHIFT, Keycode.RIGHT_ALT, Keycode.F12],  # Mute end
}

boot_anim = Anim(
    [
        "anim/boot0.bmp",
        "anim/boot1.bmp",
        "anim/boot2.bmp",
        "anim/boot3.bmp",
        "anim/boot4.bmp",
        "anim/boot5.bmp",
        "anim/boot6.bmp",
        "anim/boot7.bmp",
        "anim/boot12.bmp",
        "anim/boot12.bmp",
    ]
)
brb_anim = Anim(
    ["anim/brb/0.bmp", "anim/brb/1.bmp", "anim/brb/2.bmp", "anim/brb/3.bmp"],
    loops=99999,
)
# Establish monitor function:
async def main():
    next_vblank = time.monotonic() + .05  # 20hz refresh, if it can handle it
    next_stream_tick = time.monotonic() + .5  # check screen logic every half second
    global stream
    while True:
        # just poll inputs whenever we can, each loop should be enough anti-bounce
        await poll_inputs()
        cycle_time = time.monotonic()
        if cycle_time > next_vblank:
            next_vblank += .05
            await refresh_screen(stream.display)
        if cycle_time > next_stream_tick:
            next_stream_tick += .5
            await tick_stream()



# Establish timing-based functions:
async def refresh_screen(screen):
    if display.animation:
        display.disp_ani()
        if not display.animation.run:
            process_timer_result(False)
    if display.needs_refresh:
        display.draw_buffer()



async def poll_inputs():
    for input in key_list:
        if input.read():
            if not input.held:  # if it's only now being held:
                input.held = True
                execute_input(input.id)

        else:
            input.held = False


async def tick_stream():
    if stream.running:
        stream.tick()
    if display.countdown:
        process_timer_result(display.countdown.tick())
    light_list[0].set(stream.brb)
    light_list[1].set(stream.mute)


# Input-related
def execute_input(key):
    # Executes the command assigned to a key, or calls the subroutine it requires
    if key == "MUTE":  # We let mute run whenever, no confirmation needed.
        stream.mute = not stream.mute
        if stream.mute:  # we've inverted it, so we do the opposite
            send_keypress("MUTE")
        else:
            send_keypress("UNMUTE")
    elif key == "UI_LEFT":  # Tell whatever left/right key action to go
        if display.countdown:
            display.countdown.act = "CANCEL"
    elif key == "UI_RIGHT":
        if display.countdown:
            display.countdown.act = "CONFIRM"
    elif key == "BRB":
        # we can pause the stream with one keypress, but to resume call for a confirmation
        if stream.running:
            if stream.brb:
                prepare_timer("RESUME")
            else:
                stream.pause()
    elif key == "START_STOP":
        if stream.running:
            prepare_timer("STOP")
        else:
            prepare_timer("START")


def send_keypress(id):  # actually send the keypress to the computer
    for k in key_binds[id]:
        kbd.press(k)
    kbd.release_all()


# Timer-related


def prepare_timer(timer_type):
    if not display.countdown:  # don't double up displays
        display.countdown = Timer(display, timer_type)
        display.left_key = DispButton("Cancel", "LEFT")
        display.right_key = DispButton("Confirm", "RIGHT")
        display.left_key.draw(display.screen, True)
        display.right_key.draw(display.screen, True)
        display.blank_buffer()
        msg_offset = 128 // (7 + len(timer_type))
        display.screen.text("Really " + timer_type.lower() + "?", msg_offset, 10, 1)
        display.need_refresh = True


def process_timer_result(result):
    if result:
        if result != "AWAIT":  # If we're not being told to wait
            send_keypress(result)
            display.countdown = False
            if result == "START":
                display.countdown = False
                stream.begin_stream()
            elif result == "STOP":
                display.countdown = False
                stream.end_stream()
            elif result == "RESUME":
                display.countdown = False
                stream.resume()
        else:
            return
    else:
        display.countdown = False  # kill the display countdown
        if stream.running:
            if stream.brb:
                display.show_page("BRB")
            else:
                display.show_page("RUN")
        else:
            display.show_page("IDLE")


def time_to_str(period):
    # returns a string with the time in string format
    # HH:MM:SS
    hours = period // 3600
    mins = (period % 3600) // 60
    secs = (period % 3600) % 60
    outstr = ""
    if hours > 0:
        outstr = str(hours) + ":"
    outstr += "{:0>2}".format(mins) + ":" + "{:0>2}".format(secs)
    return outstr


# Initialize the display:
display.animation = boot_anim
# Run that bad boy
asyncio.run(main())
