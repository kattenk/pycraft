from pycraft.chunk import Chunk
from pycraft.vector import Vec3, Direction
import opensimplex, math
import time, random
import pycraft.blocks
import numpy as np
import sys
from typing import List

# Here I store a list of directions that includes diagonals at the end,
# It's used for checking adjacent blocks to check if a tree can grow somewhere.abs
# (this isn't good code and I meant to remove it later..)
directions = [
    Vec3(1, 0, 0),
    Vec3(-1, 0, 0),
    Vec3(0, 0, -1),
    Vec3(0, 0, 1),
    Vec3(1, 0, -1),
    Vec3(1, 0, 1),
    Vec3(-1, 0, -1),
    Vec3(-1, 0, 1)
]

diagonals = [
    Vec3(1, 0, -1),
    Vec3(1, 0, 1),
    Vec3(-1, 0, -1),
    Vec3(-1, 0, 1)
]

class Tree:
    def __init__(self, trunk_block: pycraft.blocks.Block, leaf_block: pycraft.blocks.Block):
        self.trunk_block = trunk_block
        self.leaf_block = leaf_block
    
    @staticmethod
    def fill_area(chunk: Chunk, min_point: Vec3, max_point: Vec3, block: pycraft.blocks.Block):
        for x in range(min_point.x, max_point.x + 1):
            for y in range(min_point.y, max_point.y + 1):
                for z in range(min_point.z, max_point.z + 1):
                    if chunk.is_within_bounds(Vec3(x, y, z)):
                        chunk.set_block(Vec3(x, y, z), block)
    
    def place_in_chunk(self, chunk: Chunk, position: Vec3, chance: int):
        if np.random.randint(1, 100) >= chance:
            return

        for direction in directions:
            check_position = Vec3(position + Vec3(0, 1, 0) + direction)

            if not chunk.is_within_bounds(check_position) or chunk.get_block(check_position):
                return
        
        trunk_height = np.random.randint(2, 4) + 1
        Tree.fill_area(chunk, position + Vec3(0, 0, 0), position + Vec3(0, trunk_height - 1, 0), self.trunk_block)
        Tree.fill_area(chunk, position + Vec3(-1, trunk_height - 1, -1), position + Vec3(1, trunk_height + 1, 1), self.leaf_block)
        
        chunk.set_block(position + Vec3(0, trunk_height + 1, 0) + np.random.choice(diagonals), None)
        chunk.set_block(position + Vec3(0, trunk_height - 1, 0) + np.random.choice(diagonals), None)

class Biome:
    def __init__(self, layers: List[pycraft.blocks.Block], trees: List[Tree] = [], tree_chance: int = 0):
        self.layers = layers
        self.trees = trees
        self.tree_chance = tree_chance

oak_tree = Tree(trunk_block=pycraft.blocks.log, leaf_block=pycraft.blocks.leaves)
spruce_tree = Tree(trunk_block=pycraft.blocks.spruce_log, leaf_block=pycraft.blocks.spruce_leaves)
snow_tree = Tree(trunk_block=pycraft.blocks.snow_log, leaf_block=pycraft.blocks.snow_leaves)
grasslands = Biome(layers=[pycraft.blocks.grass, pycraft.blocks.dirt, pycraft.blocks.stone],
                   trees=[oak_tree], tree_chance=20)
grove = Biome(layers=[pycraft.blocks.dark_grass, pycraft.blocks.dirt, pycraft.blocks.stone],
              trees=[spruce_tree], tree_chance=20)
snowy = Biome(layers=[pycraft.blocks.snow, pycraft.blocks.stone],
              trees=[snow_tree], tree_chance=10)

class Gen:
    """
    Actual procedural world generation is the most complex and defining aspect of Minecraft.
    
    and sadly it is the most lackluster part of this project at the moment.
    """

    def __init__(self, seed):
        self.seed = seed
        self.biomes = [grasslands, grove, snowy]
        opensimplex.seed(seed)
    
    def gen_chunk(self, position: Vec3) -> Chunk:
        chunk = Chunk(position)

        if chunk.chunk_position.y < 0:
            for x in range(0, Chunk.chunk_size):
                for y in range(0, Chunk.chunk_size):
                    for z in range(0, Chunk.chunk_size):
                        chunk.set_block(Vec3(x, y, z), pycraft.blocks.stone)
                    
            chunk.gen_meshes()
            return chunk
        
        for x in range(0, Chunk.chunk_size):
            for z in range(0, Chunk.chunk_size):
                elevation = 0

                def noise_with_freq(freq):
                    return opensimplex.noise2(x * freq + (freq * (16 * position.x)),
                                            z * freq + (freq * (16 * position.z)))
                
                biome = self.biomes[int(((noise_with_freq(0.005) + 1) / 2) * len(self.biomes))]
                
                # Base
                elevation_sample = noise_with_freq(0.05)
                elevation = math.floor(elevation_sample * 3) + 4
                
                # Some raised areas to make it take slightly longer before you realize how boring this terrain is :P
                raised_area_noise = noise_with_freq(0.02)
                if raised_area_noise > 0.3:
                    elevation += math.floor(raised_area_noise * 15)

                in_trees = elevation_sample > 0
                
                for y in range(0, Chunk.chunk_size):
                    # Get global y-coordinate
                    global_y = y + (position.y * 16)
                    if global_y < elevation:
                        # Get depth from the surface, assign block based on that from the biome
                        depth = elevation - global_y - 1
                        if depth < len(biome.layers):
                            chunk.set_block(Vec3(x, y, z), biome.layers[depth])
                        else:
                            chunk.set_block(Vec3(x, y, z), biome.layers[-1])
                        
                        if depth == 0 and in_trees and y < 9:
                            biome.trees[0].place_in_chunk(chunk, Vec3(x, y, z), biome.tree_chance)

        chunk.gen_meshes()
        return chunk