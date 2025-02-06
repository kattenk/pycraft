from pycraft.game import Game, Input
import glfw

if __name__ == "__main__":
    Game(title="Pycraft", window_width=1220, window_height=701, world_seed=1234, controls={
        Input.MOVE_FORWARD:  glfw.KEY_W,
        Input.MOVE_BACKWARD: glfw.KEY_S,
        Input.MOVE_LEFT:     glfw.KEY_A,
        Input.MOVE_RIGHT:    glfw.KEY_D,
        Input.JUMP:          glfw.KEY_SPACE,
        Input.PLACE:         glfw.MOUSE_BUTTON_RIGHT,
        Input.BREAK:         glfw.MOUSE_BUTTON_LEFT,
        Input.QUIT:          (glfw.KEY_Q, glfw.KEY_ESCAPE),
        Input.SWITCH_BLOCK_1: glfw.KEY_1,
        Input.SWITCH_BLOCK_2: glfw.KEY_2,
        Input.SWITCH_BLOCK_3: glfw.KEY_3,
        Input.SWITCH_BLOCK_4: glfw.KEY_4,
    }).run()