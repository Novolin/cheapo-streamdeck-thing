# Quick script to check that the pins are assigned to the right tasks


import board
from digitalio import DigitalInOut, Pull, Direction


class InputKey:
    def __init__(self, pin, text):
        self.key_obj = DigitalInOut(pin)
        self.key_obj.direction = Direction.INPUT
        self.key_obj.pull = Pull.UP
        self.text = text

    def check_val(self):
        if not self.key_obj.value: #remember, we pull down:
            print(self.text)
            return True



key_list = [  # List of input keys
    InputKey(board.GP8, "UI_LEFT"),
    InputKey(board.GP9, "UI_RIGHT"),
    InputKey(board.GP13, "BRB"),
    InputKey(board.GP27, "MUTE"),
    InputKey(board.GP5, "START_STOP")
]

keys_checked = []

while len(keys_checked) < len(key_list):
    for i in key_list:
        if i.text not in keys_checked:
            if i.check_val():
                keys_checked.append(i.text)

print("Done!")
