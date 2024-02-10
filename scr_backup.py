import adafruit_imageload
from time import time
class Image:
    # Bitmap image that can be passed to the screen display stuff
    def __init__(self, file, size_x, size_y):
        # It's only a black/white bmp so whatevs.
        self.bitmap = adafruit_imageload.load(file)[0]
        self.size_x = size_x
        self.size_y = size_y
    def draw_to_pos(self, buff, x_pos, y_pos):
        # Draws the image to a given position in the framebuffer
        for x in range(self.size_x):
            for y in range(self.size_y):
                buff.pixel(x + x_pos,y + y_pos ,self.bitmap[x + (self.size_x * y)])
    

# The button that is shown on screen, just the display part
class DisplayButton:
    def __init__(self, text, position):
        self.text = text[0:9] # truncate to 9 characters
        if position == "left": #set the position for the text, this is where it will be centered
            self.position = 3
        else:
            self.position = 67
    def draw(self, do_fill, screen):
        # blits the data to the screen buffer
        # screen will require a refresh afterwards
        screen.fill_rect(self.position -1, 51, 60, 11, do_fill)
        x_pos = self.position + 60//len(self.text) # Center it nicely :)
        screen.text(self.text, x_pos, 53, not do_fill)

class Screen:
    def __init__(self, screen_obj, left_button, right_button):
        # parent class for all screens,
        #renders the left and right buttons and their container squares
        self.bg = Image("img/bg.bmp", 128, 64)
        self.screen = screen_obj
        self.left_button = left_button
        self.right_button = right_button
        self.blink_left = False
        self.blink_right = False
        self.needs_refresh = True

    def draw_screen_template(self):
        self.bg.draw_to_pos(self.screen, 0,0)
        self.draw_buttons()
        self.screen.show()

    def draw_buttons(self):
        self.left_button.draw(False, self.screen)
        self.right_button.draw(False, self.screen)

    def left_action(self): # what to do when the left button is pressed, default scroll
        self.blink_left = not self.blink_left
    def right_action(self): # what to do when the right button is pressed, default scroll
        self.blink_right = not self.blink_right
    def draw(self):
        # Draw the content to the screen. changes per screen
        pass
    def cover_contents(self):
        self.screen.fill_rect(2,2,124,44,0)
        self.screen.show()

class MainScreen(Screen):
    # Default screen, doesn't do a whole bunch
    def __init__(self, screen_obj):
        self.left_button = DisplayButton("Previous", "left")
        self.right_button = DisplayButton("Next", "right")
        super().__init__(screen_obj, self.left_button,  self.right_button)
        self.img = Image("img/test.bmp", 124,46)

    def draw(self):
        self.img.draw_to_pos(self.screen, 2, 2)
        self.screen.show()
    
class StreamRunning(Screen):
    def __init__(self, screen_obj, stream_obj):
        self.stream = stream_obj
        self.left_button = DisplayButton("Previous", "left")
        self.right_button = DisplayButton("Next", "right")
        super().__init__(screen_obj, self.left_button, self.right_button)
    def draw(self):
        self.screen.text("STREAMO", 6, 20, 1, size = 2)

class CountScreen(Screen):
    # Parent class for countdown screens
    def __init__(self, screen_obj, text):
        self.time_result = 0
        self.query_text = "Really " + text + "?"
        self.count_running = False
        self.count_time = time()
        self.end_time = 0
        self.left_button = DisplayButton("Cancel", "left")
        self.right_button = DisplayButton("Confirm", "right")
        super().__init__(screen_obj, self.left_button, self.right_button)
    
    def start_countdown(self, wait = 10):
        self.count_time = time()
        self.end_time = self.count_time + wait
        self.count_running = True
        self.count_state = 0
        self.cover_contents()
        center = 2 + 124//len(self.query_text)
        self.screen.text(self.query_text, center,7,1)
        self.screen.fill_rect(4,29,120,16,1)
        self.screen.show()
        self.time_result = 0

    
    def draw(self):
        remaining = self.end_time - time()
        if remaining >0:
            self.screen.fill_rect(4,29,120 - (12 * remaining), 16 ,0)
            self.screen.show()
        else:
            self.time_result = 1
    def left_action(self):
        self.time_result = 1
    def right_action(self):
        self.time_result = 2

class StreamPaused(Screen):
    def __init__(self, screen_obj):
        super().__init__(screen_obj, "Resume", "End")
        # display a lil animation? 