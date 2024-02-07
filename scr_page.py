# FILE 2: THIS IS FOR THE SCREEN THINGS
# HANDLING SCREEN LOGIC AND WHAT NOT
# prefer loading images from file because memory

class Screen:
    def __init__(self, screen_obj):
        self.display = screen_obj
        self.screen_page = 0
        self.await_keys = False # are we waiting for a keypress?
        self.clock_string = "00:00:00"
        self.page_list = []


class Page:
    def __init__(self, page_name, key_func_1 = False, key_func_2 = False):
        self.page_name = page_name
        if key_func_1:
            self.key_func_1 = key_func_1


        self.screen_data =

