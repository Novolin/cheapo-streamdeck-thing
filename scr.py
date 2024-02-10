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

class Clock