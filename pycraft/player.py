from pycraft.camera import Camera
from pycraft.vector import Vec3, Axis, Normal
from pycraft.inputs import Input
from pycraft.world import World
from pycraft.blocks import Block
from pycraft.render import Mesh, TextureSet
from pycraft.physics import Physics, AABB
from typing import Tuple
import pycraft.blocks
import math, random

class Player:
    """Singleton that represents the player."""

    def __init__(self, position: Vec3, camera: Camera, world: World):
        self.position = position
        self.camera = camera

        # The player holds a reference to the world that it uses to check for
        # collisions and edit blocks.
        self.world = world

        self.movement_speed = 5.3
        self.look_sensitivity = 5
        self.looking_at: Tuple[Vec3, Normal] = (None, None)
        self.selection_box: Mesh = None
        self.reach = 6

        # Attributes relating to placing and breaking blocks:
        self.holding_block: Block = pycraft.blocks.log
        self.inventory = [pycraft.blocks.log, pycraft.blocks.planks, pycraft.blocks.stone, pycraft.blocks.glass]
        self.placed: bool = False
        self.breaking_progress: float = 0.0
        self.breaking_damage: Tuple[int, Mesh] = (-1, None)

        self.bounding_box = AABB(self.position, Vec3(-0.3, 0.2, -0.3), Vec3(0.3, 1.6, 0.3))
        self.velocity: Vec3 = Vec3(0)
        self.jump_force = 8
        self.gravity = 30
        self.is_on_ground: bool = True

        self.update_camera_position()
    
    def update_camera_position(self):
        """The camera should always be 1.6 blocks above the player's feet."""
        self.camera.position = self.position + Vec3(0, 1.6, 0)

    def move(self, inputs, time_delta):
        """Handles player movement."""

        if not any(move_input in inputs for move_input in [
                Input.MOVE_FORWARD,
                Input.MOVE_BACKWARD,
                Input.MOVE_LEFT,
                Input.MOVE_RIGHT,
                Input.JUMP]) and self.is_on_ground:
            return
        
        self.bounding_box.position = self.position

        # Calculate movement direction based on inputs
        move_impulse = Vec3(0, 0, 0)
        yaw_rad = math.radians(self.camera.yaw)

        # Move right
        if Input.MOVE_RIGHT in inputs:
            move_impulse.x += math.cos(yaw_rad)
            move_impulse.z += math.sin(yaw_rad)
        
        # Move forward
        if Input.MOVE_FORWARD in inputs:
            move_impulse.x += math.sin(yaw_rad)
            move_impulse.z -= math.cos(yaw_rad)
        
        # Move left
        if Input.MOVE_LEFT in inputs:
            move_impulse.x -= math.cos(yaw_rad)
            move_impulse.z -= math.sin(yaw_rad)
        
        # Move backward
        if Input.MOVE_BACKWARD in inputs:
            move_impulse.x -= math.sin(yaw_rad)
            move_impulse.z += math.cos(yaw_rad)
        
        # Normalize movement direction
        move_impulse = move_impulse.normalize()

        # Apply the movement to the velocity
        self.velocity.x = move_impulse.x * self.movement_speed
        self.velocity.z = move_impulse.z * self.movement_speed

        if Input.JUMP in inputs and self.is_on_ground:
            self.velocity.y = self.jump_force
            self.is_on_ground = False
        
        if not self.is_on_ground:
            self.velocity.y -= self.gravity * time_delta
            self.velocity.y = max(self.velocity.y, -15)

            if Physics.get_collision_normal(self.world, self.bounding_box, Vec3(0, -0.25, 0)) == Normal.TOP.value:
                self.is_on_ground = True

        # Apply the force to the position
        self.position += Physics.apply_force(self.world, self.bounding_box, self.velocity * time_delta)
        
        # Update camera position based on the player position
        self.update_camera_position()
        self.update_looking_at()
    
    def look(self, dx, dy, aspect_ratio, time_delta):
        """Handles making the player change rotation based on mouse movement."""
        adjusted_sensitivity = self.look_sensitivity * aspect_ratio

        self.camera.yaw += (dx * adjusted_sensitivity) * time_delta
        self.camera.pitch -= (dy * adjusted_sensitivity) * time_delta

        self.camera.pitch = max(-89, min(89, self.camera.pitch))
        self.camera.update_rotation()
        self.update_looking_at()
    
    def break_and_place(self, inputs, time_delta):
        # Handle placing
        if Input.PLACE in inputs and not self.placed:
            looking_at_block, side = self.looking_at

            if looking_at_block:
                # We don't want to let the player place blocks where they're standing
                if (looking_at_block + side.value) not in self.bounding_box.get_occupied_positions():
                    self.world.set_block(looking_at_block + side.value, self.holding_block)
                    self.looking_at = (None, None)
                    self.update_looking_at()
                    self.placed = True
            
        elif Input.PLACE not in inputs and self.placed:
            self.placed = False
        
        # Handle breaking
        if Input.BREAK in inputs:
            looking_at_block, _ = self.looking_at

            if looking_at_block:
                # If we've finished breaking, actually remove the block:
                if self.breaking_progress >= self.world.get_block(looking_at_block).break_time:
                    self.world.set_block(looking_at_block, None)
                    self.update_looking_at()
                    self.breaking_progress = 0
                    self.update_looking_at()
                else:         
                    self.breaking_progress += time_delta
                
                self.update_breaking_damage()
        else:
            if self.breaking_progress != 0:
                self.breaking_progress = 0
                self.update_breaking_damage()
    
    def switch_block(self, inputs):
        if Input.SWITCH_BLOCK_1 in inputs:
            self.holding_block = self.inventory[0]
        if Input.SWITCH_BLOCK_2 in inputs:
            self.holding_block = self.inventory[1]
        if Input.SWITCH_BLOCK_3 in inputs:
            self.holding_block = self.inventory[2]
        if Input.SWITCH_BLOCK_4 in inputs:
            self.holding_block = self.inventory[3]
    
    def update_breaking_damage(self):
        last_stage, mesh = self.breaking_damage
        looking_at_block, _ = self.looking_at

        if self.breaking_progress == 0:
            if mesh:
                if mesh in self.world.overlay_meshes:
                        self.world.overlay_meshes.remove(mesh)
        else:
            progress_percentage = self.breaking_progress / self.world.get_block(looking_at_block).break_time
            current_stage = int(progress_percentage * 4)

            if last_stage != current_stage:
                if mesh:
                    if mesh in self.world.overlay_meshes:
                        self.world.overlay_meshes.remove(mesh)
                    mesh.discard()

                new_mesh = Mesh(looking_at_block - Vec3(0.005), Mesh.generate_cuboid(Vec3(1.01, 1.01, 1.01),
                                Mesh.generate_uniform_texture_map(Block.breaking_animation[current_stage])), Block.breaking_animation_set)

                self.world.overlay_meshes.append(new_mesh)
                self.breaking_damage = (current_stage, new_mesh)

    def update_looking_at(self):
        """Handles determining which block in the world the player is looking at"""
        
        hit, normal = Physics.raycast(world=self.world,
                                      origin=self.camera.position,
                                      direction=self.camera.forward,
                                      reach=self.reach)
        
        last_hit, last_normal = self.looking_at

        if (hit, normal) == (last_hit, last_normal):
            return

        self.breaking_progress = 0

        if hit:
            if normal != last_normal:
                if self.selection_box:
                    if self.selection_box in self.world.overlay_meshes:
                        self.world.overlay_meshes.remove(self.selection_box)
                
                    if self.selection_box.vbo:
                        self.selection_box.discard()
                
                excluded_faces = list(Normal)
                excluded_faces.remove(normal)

                selection_box_textures = TextureSet()

                self.selection_box = Mesh(position=Vec3(hit) + (normal.value * 0.001),
                                          data=Mesh.generate_cuboid(Vec3(1),
                                          layers=Mesh.generate_uniform_texture_map(selection_box_textures.add_texture("selection_box")),
                                          exclude_faces=excluded_faces),
                                          textures=selection_box_textures)

                self.world.overlay_meshes.append(self.selection_box)
            elif last_hit != hit:
                self.selection_box.position = hit + (normal.value * 0.001)
        else:
            self.selection_box.cull_face = 'front'
        
        self.looking_at = (hit, normal)