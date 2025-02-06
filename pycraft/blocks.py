from pycraft.vector import Normal as N
from pycraft.vector import Normal as Normal
from pycraft.render import TextureSet
import hashlib

class Block:
    """The Block class represents a type of block"""

    # We store some things that are static things
    # relating to the Block class, such as the textures,
    # and a map of IDs to block classes.
    block_textures: TextureSet = TextureSet()
    blocks_map: dict = {}

    breaking_animation_set = TextureSet()
    breaking_animation = [
        breaking_animation_set.add_texture("breaking_animation1"),
        breaking_animation_set.add_texture("breaking_animation2"),
        breaking_animation_set.add_texture("breaking_animation3"),
        breaking_animation_set.add_texture("breaking_animation4"),
        breaking_animation_set.add_texture("breaking_animation5")
    ]

    def __init__(self, name: str, textures={}, break_time: float = 0.3):
        internal_name = name.lower().replace(" ", "_")
        self.name = name
        self.block_id = int(hashlib.shake_128(name.lower().encode()).hexdigest(4), 16)
        self.textures = {}
        self.break_time = break_time

        for normal in Normal:
            self.textures[normal] = self.block_textures.add_texture(
                textures[normal] if normal in textures.keys() else internal_name
            )
        
        self.blocks_map[self.block_id] = self
        
grass = Block(
    name = "Grass",
    textures = {
        N.RIGHT:  'grass_side',
        N.LEFT:   'grass_side',
        N.FRONT:  'grass_side',
        N.BACK:   'grass_side',
        N.TOP:    'grass',
        N.BOTTOM: 'dirt'
    },
    break_time = 0.5
)

dark_grass = Block(
    name = "Dark Grass",
    textures = {
        N.RIGHT:  'dark_grass_side',
        N.LEFT:   'dark_grass_side',
        N.FRONT:  'dark_grass_side',
        N.BACK:   'dark_grass_side',
        N.TOP:    'dark_grass',
        N.BOTTOM: 'dirt'
    },
    break_time = 0.5
)

dirt = Block(
    name = "Dirt",
    break_time = 0.5
)

stone = Block(
    name = "Stone",
    break_time = 1
)

glass = Block(
    name = "Glass",
    break_time = 0.3
)

planks = Block(
    name = "Planks",
    break_time = 0.8
)

log = Block(
    name = "Log",
    break_time = 0.8
)

spruce_log = Block(
    name = "Spruce Log",
    break_time = 0.8
)

leaves = Block(
    name = "Leaves",
    break_time = 0.2
)

spruce_leaves = Block(
    name = "Spruce Leaves",
    break_time = 0.2
)

snow = Block(
    name = "Snow",
    textures = {
        N.RIGHT:  'snow_side',
        N.LEFT:   'snow_side',
        N.FRONT:  'snow_side',
        N.BACK:   'snow_side',
        N.TOP:    'snow',
        N.BOTTOM: 'dirt'
    },
    break_time = 0.5
)

snow_leaves = Block(
    name = "Snow Leaves",
    break_time = 0.2
)

snow_log = Block(
    name = "Snow Log",
    break_time = 0.8
)