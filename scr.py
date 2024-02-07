import time


class Screen:
    def __init__(self, screen_obj, left_button, right_button):
        # parent class for all screens,
        #renders the left and right buttons and their container squares
        self.screen = screen_obj
        self.left_button = left_button
        self.right_button = right_button
        self.blink_left = False
        self.blink_right = False
        if len(left_button) > 10:
            self.left_button = left_button[0:9]
        if len(right_button) > 10:
            self.right_button = right_button[0:9]

    def draw_screen_template(self):
        self.screen.fill(0)
        self.screen.rect(0, 0, 128, 64, 1)
        self.screen.rect(3, 49, 58, 12, 1)
        self.screen.rect(68, 49, 58, 12, 1)
        self.screen.pixel(3, 49, 0)
        self.screen.pixel(3, 60, 0)
        self.screen.pixel(60, 49, 0)
        self.screen.pixel(60, 60, 0)
        self.screen.pixel(68, 49, 0)
        self.screen.pixel(68, 60, 0)
        self.screen.pixel(125, 49, 0)
        self.screen.pixel(125, 60, 0)
        self.screen.text(self.left_button, 6, 51, 1)
        self.screen.text(self.right_button, 71, 51, 1)
        self.screen.show()

    def do_blink(self, blink_state):
        if self.blink_left:
            self.screen.rect(4, 50, 56, 10, blink_state)
            self.screen.text(self.left_button, 6, 51, not blink_state)
        if self.blink_right:
            self.screen.rect(4, 50, 56, 10, blink_state)
            self.screen.text(self.right_button, 71, 51, not blink_state)

    def draw(self):
        # Draw the content to the screen.
        pass


class ClockScreen(Screen):
    def __init__(self, screen_obj):
        super().__init__(screen_obj, "Previous", "Next")
        self.current_time = time.localtime(time.time())
        self.time_display = str(self.current_time.tm_hour)
        #+ ":" + str(self.current_time.tm_min)
        #+ ":" + str(self.current_time[5])

    def draw(self):
        self.screen.text(self.time_display, 6, 20, 2)
        self.screen.show()
