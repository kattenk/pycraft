from pycraft.render import Mesh, TextureSet
from pycraft.vector import Direction
from pycraft.vector import Normal as N
from pycraft.vector import Vec3
from pycraft.blocks import Block
import pycraft.blocks
import random

class Chunk:
    chunk_size = 16

    def __init__(self, chunk_position: Vec3):
        self.chunk_position = chunk_position
        self.blocks = [[[None for _ in range(self.chunk_size)]
                              for _ in range(self.chunk_size)]
                              for _ in range(self.chunk_size)]
        
        self.meshes = []
        
        # used by World for unloading
        self.loaded_at_time = 0.0

        self.gen_meshes()
    
    def gen_meshes(self):
        """
        This is the chunk mesh generation method, which turns the internal representation of a chunk into
        a list of 3D meshes that can be rendered on screen.

        It does this through a simple algorithm in the family of "Greedy Meshing". having a discrete cube
        for each block would be wasteful of GPU resources and time to render, so the algorithm combines
        continuous regions of blocks into larger cuboid shapes, which then become the meshes.

        you can think of the algorithm as a block being "greedy" and "eating" other blocks in all directions,
        until it can't find more blocks to combine with, at which point it solidifies into a mesh.
        """
        
        self.unload()

        # Keep a set of the blocks that have already been "consumed", stored as position tuples (x, y, z)
        consumed_blocks = set()

        # Use get_area() to retrieve the entire chunk,
        # which I find to be cleaner than massive nests of for-loops.
        whole_chunk = self.get_area(Vec3(0), Vec3(self.chunk_size))

        # Loops over every block in the chunk
        for x, y, z, block in whole_chunk:
            if (x, y, z) in consumed_blocks:
                continue

            if block is None:
                continue

            position = Vec3(x, y, z)
            size = Vec3(1, 1, 1)

            def grow(position: Vec3, size: Vec3, direction: Direction):
                """
                This function expands the cuboid, specified by two points,
                by 1 unit in the given direction in a right-handed coordinate system
                """
                grown_pos = Vec3(position.x, position.y, position.z)
                grown_size = Vec3(size.x, size.y, size.z)

                if direction == Direction.RIGHT:
                    grown_size.x += 1
                elif direction == Direction.LEFT:
                    grown_pos.x -= 1
                    grown_size.x += 1
                elif direction == Direction.UP:
                    grown_size.y += 1
                elif direction == Direction.DOWN:
                    grown_pos.y -= 1
                    grown_size.y += 1
                elif direction == Direction.BACKWARD:
                    grown_size.z += 1
                elif direction == Direction.FORWARD:
                    grown_pos.z -= 1
                    grown_size.z += 1

                return grown_pos, grown_size

            def can_grow(position: Vec3, size: Vec3, direction: Direction, block):
                grow_pos, grow_size = grow(position, size, direction)

                if not self.is_within_bounds(grow_pos):
                    return False
                
                if not self.is_within_bounds(grow_pos + grow_size - Vec3(1, 1, 1)):
                    return False

                for inner_x, inner_y, inner_z, inner_block in self.get_area(grow_pos, grow_pos + grow_size):
                    # Do not grow if we can't comebine with this block
                    if inner_block is not block:
                        return False
                    
                    # Do not grow into blocks that have been consumed already
                    if (inner_x, inner_y, inner_z) in consumed_blocks:
                        return False
                
                return True
            
            for direction in Direction:
                while can_grow(position, size, direction, block):
                    position, size = grow(position, size, direction)

            for x, y, z, _ in self.get_area(position, position + size):
                consumed_blocks.add((x, y, z))
            
            chunk_offset = self.chunk_position * self.chunk_size

            cull_face = 'back'
            # Here I tried to mess with the culling to try and fix the leaf issues
            # (but it didn't work so I removed it)
            # if block == pycraft.blocks.leaves:
            #     cull_face = 'front'
            
            self.meshes.append(
                Mesh(
                    position=chunk_offset + position,
                    data=Mesh.generate_cuboid(
                        scale=size,
                        layers=self.get_block(Vec3(x, y, z)).textures
                    ),
                    textures=Block.block_textures,
                    cull_face=cull_face
                )
            )

    def unload(self):
        """
        This is supposed to clean the slate for this chunk, I have no idea if I've done this correctly,
        there are probably tons of nightmarish bugs that can happen with stuff like this.

        it seems to work ok.
        """
        for mesh in self.meshes:
            mesh.data = None
            self.meshes.remove(mesh)
            mesh.discard()
        
        self.meshes = []
    
    def get_area(self, min_point: Vec3, max_point: Vec3):
        """Returns a list of blocks within the given area defined by min_point and max_point"""
        blocks_in_area = []
        
        for x in range(min_point.x, max_point.x):
            for y in range(min_point.y, max_point.y):
                for z in range(min_point.z, max_point.z):
                    if self.is_within_bounds(Vec3(x, y, z)):
                        blocks_in_area.append((x, y, z, self.blocks[x][y][z]))
                    else:
                        raise Exception(f"tried to get area that goes out of bounds {min_point = } {max_point = }")
            
        return blocks_in_area
        
    def is_within_bounds(self, position: Vec3) -> bool:
        """Checks if a chunk-space coordinate is within the chunk's bounds"""

        # We must check if the coordinate is negative on any of the axis first because
        # Python accepts negative indices in lists (-1 means the last element, etc)
        if position.x < 0 or position.y < 0 or position.z < 0:
            return False

        try:
            _ = self.blocks[position.x][position.y][position.z]
            return True
        except IndexError:
            return False
        
    def set_block(self, position: Vec3, new_block: pycraft.blocks.Block, regenerate_meshes = False):
        if self.is_within_bounds(position):
            if new_block:
                self.blocks[position.x][position.y][position.z] = new_block.block_id
            else:
                self.blocks[position.x][position.y][position.z] = None
            
            if regenerate_meshes:
                self.gen_meshes()

    def get_block(self, position: Vec3):
        if self.is_within_bounds(position):
            block = self.blocks[position.x][position.y][position.z]

            if block is not None:
                return Block.blocks_map[self.blocks[position.x][position.y][position.z]]
            else:
                return None
        else:
            return Exception(f"Attempted to get_block outside chunk {position}")
