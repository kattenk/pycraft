from pycraft.render import Mesh, TextureSet
from pycraft.vector import Normal as N
from pycraft.vector import Normal as Normal
from pycraft.vector import Vec3
from pycraft.chunk import Chunk
from pycraft.gen import Gen
import pycraft.blocks
import glfw
import math, random, queue
import multiprocessing

class World:
    def __init__(self, seed):
        self.seed = seed
        self.chunks = {}
        self.gen_process = multiprocessing.Process()
        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()

        def gen_worker(seed, input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue):
            gen = Gen(seed)

            while True:
                chunk_to_generate = input_queue.get()

                if chunk_to_generate == "stop":
                    break

                output_queue.put(gen.gen_chunk(Vec3(chunk_to_generate)))

        self.gen_process = multiprocessing.Process(target=gen_worker, args=(self.seed, self.input_queue, self.output_queue))
        self.gen_process.start()

        self.loading_chunks = []

        sky_textures = TextureSet()
        self.skybox = Mesh(Vec3(-0.5, -0.5, -0.5), Mesh.generate_cuboid(Vec3(1, 1, 1), {
            N.FRONT: sky_textures.add_texture("sky_side"),
            N.BACK: sky_textures.add_texture("sky_side2"),
            N.LEFT: sky_textures.add_texture("sky_side3"),
            N.RIGHT: sky_textures.add_texture("sky_side"),
            N.TOP: sky_textures.add_texture("sky_top"),
            N.BOTTOM: sky_textures.add_texture("sky_top")
        }), sky_textures, cull_face='front')

        self.last_player_position = Vec3(0)

        # We keep an extra list of meshes for "overlays"
        # this is used for displaying the selection box on the face
        # the player's looking at, as well as the block breaking progress
        self.overlay_meshes = []
    
    def stop_gen_process(self):
        self.input_queue.put("stop")
    
    def load_chunks(self, player_position: Vec3, load_distance: int):
        """
        Called every frame and handles the loading and unloading of chunks based on player location,
        and a distance value for how far to load chunks from the player in each direction.
        """

        while not self.output_queue.empty():
            chunk: Chunk = self.output_queue.get()
            x, y, z = chunk.chunk_position
            self.chunks[(x, y, z)] = chunk
            chunk.loaded_at_time = glfw.get_time()
            self.loading_chunks.remove((x, y, z))

        # We don't want to re-calculate loaded chunks for every single tiny movement
        # instead, only re-calculate when the player moves by a block
        if player_position.floor() != self.last_player_position:
            # Get the current chunk of the player
            player_chunk = player_position // Chunk.chunk_size

            # Make a list of every chunk that should be loaded in the specified radius
            chunks_in_range = []
            for x in range(player_chunk.x - load_distance, player_chunk.x + load_distance + 1):
                for z in range(player_chunk.z - load_distance, player_chunk.z + load_distance + 1):
                    for y in range(player_chunk.y - 1, player_chunk.y + 1):
                        chunks_in_range.append((x, y, z))
            
            chunks_to_unload = [chunk for chunk in self.chunks.keys() if chunk not in chunks_in_range]

            # Unload chunks out of range. we only unload them if they've been loaded for 10 seconds
            # this is a basic solution to prevent rapid loading and unloading as the player goes back and forth.
            for chunk in chunks_to_unload:
                if abs(self.chunks[chunk].loaded_at_time - glfw.get_time()) < 10:
                    continue
                
                self.chunks[chunk].unload()
                del self.chunks[chunk]

            # Load chunks in range
            for chunk in chunks_in_range:
                if chunk not in self.chunks and chunk not in self.loading_chunks:
                    self.loading_chunks.append(chunk)
                    self.input_queue.put(chunk)
            
            # Set the last player position to the new block location,
            # so we can detect when the player moves by another block
            self.last_player_position = player_position.floor()

    def get_chunk(self, chunk_position: Vec3) -> Chunk:
        """Retrieves a Chunk by it's location"""
        return self.chunks.get((chunk_position.x, chunk_position.y, chunk_position.z))
    
    def world_to_chunk_location(self, world_position: Vec3) -> Vec3:
        """Calculates the chunk location that contains the world-space position passed"""
        return world_position // Chunk.chunk_size
    
    def get_block(self, position: Vec3) -> pycraft.blocks.Block:
        """Retrieves a block by position in world space."""

        in_chunk: Chunk = self.get_chunk(self.world_to_chunk_location(position))

        if in_chunk is not None:
            position = position.floor() - (in_chunk.chunk_position * Chunk.chunk_size)
            return in_chunk.get_block(position)

    def set_block(self, position: Vec3, new_block: pycraft.blocks.Block):
        """Sets a block at the given position in world space."""

        in_chunk: Chunk = self.get_chunk(self.world_to_chunk_location(position))

        if in_chunk is not None:
            position = position.floor() - (in_chunk.chunk_position * Chunk.chunk_size)
            in_chunk.set_block(position, new_block, regenerate_meshes=True)
