import glfw, moderngl, math, enum
from pycraft.vector import Vec3
from pycraft.render import Renderer
from pycraft.player import Player
from pycraft.camera import Camera
from pycraft.world import World
from pycraft.inputs import Input
import pycraft.blocks

class Game:
    """The Game class is a singleton that handles opening and running the game"""
    
    def __init__(self, title, window_width, window_height, controls, world_seed):
        # Initialize GLFW
        if not glfw.init():
            return
        
        # Create the window and its OpenGL context
        self.window = glfw.create_window(window_width, window_height, title, None, None)

        if not self.window:
            glfw.terminate()
            return
        
        # Make the window's context current
        glfw.make_context_current(self.window)

        # Attempt to center the mouse in the window
        glfw.set_cursor_pos(self.window, window_width / 2, window_height / 2)

        self.aspect_ratio = window_width/window_height
        
        # Store a set of active Inputs
        self.inputs = set()

        # This will setup callbacks that will process keys and mouse clicks and map them to Inputs depending on controls
        self.configure_input(controls)

        self.last_time = glfw.get_time()
        self.mouse_position = (0, 0)
        self.last_mouse_position = (0, 0)

        self.world = World(world_seed)
        self.player = Player(position=Vec3(0, 44, 0),
                             camera=Camera(aspect_ratio=self.aspect_ratio),
                             world=self.world)

        self.renderer = Renderer(self.player.camera, self.world)
    
    def run(self):
        """This is the Main Game Loop, calling run() enters a loop that will run until the game finishes."""

        while not glfw.window_should_close(self.window):
            # "time_delta" is a value that contains the time passed since the last frame,
            # this is done so we can make our code frame-rate independant.
            #
            # Say, you have a function that moves the player based on movement keys..
            # you run it every frame.. so the player will move faster on faster computers,
            # to stop this and make it move the same speed regardless of computer speed,
            # we multiply our movements by time_delta. "Delta" means "difference"
            current_time = glfw.get_time()
            time_delta = current_time - self.last_time
            self.last_time = current_time

            # Handle mouse position updates
            if self.mouse_position != self.last_mouse_position:
                (mx, my) = self.mouse_position
                (lx, ly) = self.last_mouse_position
                dx, dy = mx - lx, my - ly

                self.player.look(dx, dy, self.aspect_ratio, time_delta)
                self.last_mouse_position = self.mouse_position

            # Hook our quitting inputs up to GLFW's window closing mechanism
            if Input.QUIT in self.inputs:
                glfw.set_window_should_close(self.window, True)
            
            self.player.move(self.inputs, time_delta) # Do player movement logic
            self.player.break_and_place(self.inputs, time_delta) # Handle block editing
            self.player.switch_block(self.inputs)
            self.world.load_chunks(self.player.position, 2) # Loads and unloads chunks depending on player position

            # If there's no block under the players feet, they aren't on the ground -- This is awful code btw
            if not self.world.get_block(self.player.position - Vec3(0, 1, 0)):
                self.player.is_on_ground = False
            
            # Render the game
            self.renderer.render(time_delta)

            # Swap front and back buffers
            glfw.swap_buffers(self.window)
        
            # Poll for and process events
            glfw.poll_events()
        
        # My attempt to stop the process where we generate the world,
        # I don't think it even works. lol
        self.world.stop_gen_process()

        # Unload GLFW after the window closes
        glfw.terminate()
    
    def configure_input(self, controls):
        def key_callback(window, key, scancode, action, mods):
            for control, binding in controls.items():
                # Support tuples for binding multiple keys to the same input
                if (isinstance(binding, tuple) and key in binding) or key == binding:
                    if action == glfw.PRESS:
                        self.inputs.add(control)
                    elif action == glfw.RELEASE:
                        self.inputs.discard(control)

        def mouse_position_callback(window, x, y):
            self.mouse_position = (x, y)
        
        def mouse_button_callback(window, button, action, mods):
            for control, binding in controls.items():
                if button == binding:
                    if action == glfw.PRESS:
                        self.inputs.add(control)
                    elif action == glfw.RELEASE:
                        self.inputs.discard(control)
        
        glfw.set_key_callback(self.window, key_callback)
        glfw.set_cursor_pos_callback(self.window, mouse_position_callback)
        glfw.set_mouse_button_callback(self.window, mouse_button_callback)
        glfw.set_input_mode(self.window, glfw.CURSOR, glfw.CURSOR_DISABLED)