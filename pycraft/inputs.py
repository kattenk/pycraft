import enum

class Input(enum.Enum):
    """An action that can be reacted to by the game"""
    MOVE_FORWARD = 1
    MOVE_BACKWARD = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    JUMP = 5
    PLACE = 6
    BREAK = 7
    QUIT = 8
    SWITCH_BLOCK_1 = 9
    SWITCH_BLOCK_2 = 10
    SWITCH_BLOCK_3 = 11
    SWITCH_BLOCK_4 = 12