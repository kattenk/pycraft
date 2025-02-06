from pycraft.vector import Vec3, Axis, Normal
from pycraft.world import World
from typing import List, Tuple
import math

class AABB:
    """
    Describes an Axis-Aligned Bounding Box (AABB) in 3D space,
    this is used for player collisions. the player is not a single point in space,
    nor a set of points, instead it is a volume defined by min_point and max_point.
    """
    def __init__(self, position: Vec3, min_point: Vec3, max_point: Vec3):
        self.position = position
        self.min_point = min_point
        self.max_point = max_point
    
    def get_occupied_positions(self) -> List[Vec3]:
        """Returns a list of world-space positions that this AABB occupies."""
        min_point = self.position + self.min_point
        max_point = self.position + self.max_point
        
        occupied_positions = []

        for x in range(math.floor(min_point.x), math.floor(max_point.x) + 1):
            for y in range(math.floor(min_point.y), math.floor(max_point.y) + 1):
                for z in range(math.floor(min_point.z), math.floor(max_point.z) + 1):
                    occupied_positions.append(Vec3(x, y, z))
        
        return occupied_positions
    
class Physics:
    """
    Does "physics" stuff (AABB-world collision, raycast)

    I made this system in a more pure style because I was tired of adding to the tangled mess
    of singletons that all reference eachother.

    All my collision system basically boils down to is this:

    ```
    if going_to_hit_wall():
        dont()
    ```

    Voxel games are probably the easiest 3D games to make collision systems for.
    since the world is just a grid of axis-aligned blocks, and we apply a force
    one axis at a time, if that force makes the AABB collide with the world,
    the correct response normal will always be the opposite of the normalized force.
    """
    @staticmethod
    def get_collision_normal(world: World, bounding_box: AABB, force: Vec3):
        moved_box = AABB(Vec3(bounding_box.position), 
                         bounding_box.min_point + force,
                         bounding_box.max_point + force)
        
        # We get correct collisions by creating a new AABB based on the players AABB,
        # with the force applied, and checking each position returned by get_occupied_positions()
        # to see if there's a block there, if there is, return the opposite of the normalized force.
        for position in moved_box.get_occupied_positions():
            if world.get_block(position):
                return force.normalize() * -1

    @staticmethod
    def apply_force(world: World, bounding_box: AABB, force: Vec3) -> Vec3:
        """
        Applies a force to an AABB, considering collisions with the world,
        and returns the new force with the collisions applied.

        We use a common technique called "Separating axis theorem" (SAT) which calculates
        collisions one axis at a time, because if we didn't there would be issues with
        diagonal forces glitching you through blocks, SAT removes diagonal forces by breaking
        down each force into 3 straight, axis-aligned forces instead.

        without SAT, no collision detected:
                  ┌────┐
                  │    │
              X   │    │
                  │    │
                  └────┘
            ┌────┐      
            │    │     
            │    │   X  
            │    │      
            └────┘       
        
        with SAT, collision detected and movement stopped:
                  ┌────┐
                  │    │
              X◄──┼──┐ │
                  │  │ │
                  └──┼─┘
            ┌────┐   │  
            │    │   │  
            │    │   X  
            │    │      
            └────┘      
        """

        final_force = Vec3(0)

        for axis in Axis:
            # Makes a vector with zero on all the "axis" except the specified one
            force_on_axis = force.on_axis(axis)

            normal = Physics.get_collision_normal(world, bounding_box, force_on_axis)

            if normal:
                # This is where we do the actual "sliding", we don't want players to get stuck on walls.
                # instead we want to smoothly slide off of them. you can think of this as subtracting the portion of the force
                # that's in the direction of the normal of the face we're supposed to slide along.
                # It's quite possible this stuff could be improved substantially, I just copied it from some old code
                force_on_axis -= normal * force_on_axis.dot(normal)

            # Apply the force on this axis
            final_force += force_on_axis
        
        # Return the force
        return final_force
    
    def raycast(world: World, origin: Vec3, direction: Vec3, reach: int) -> Tuple[Vec3, Normal]:
        """
        Traces a straight line (casts a ray) from the specified origin in the specified direction,
        until it either hits a block in the world, or exceeds 'reach'.
        
        It returns a tuple of either (Block position hit, Normal) or (None, None)

        This is used to determine what block and which face of that block the player is looking at.
        """
        distance = 0
        current_position: Vec3 = origin

        # To do the raycast we must divide the ray into positions along the ray and check those
        while distance <= reach:
            check_position = (origin) + (direction * distance)

            for axis in Axis:
                change_on_axis = ((check_position.on_axis(axis) - current_position.on_axis(axis)))

                # If the change on the axis made us cross a block-boundary
                if (current_position + change_on_axis).floor() != current_position.floor():
                    if world.get_block((current_position + change_on_axis).floor()):
                        for normal in Normal:
                            if normal.value == (current_position.floor() - ((current_position + change_on_axis).floor())):
                                return (current_position + change_on_axis).floor(), normal
                
                current_position += change_on_axis

            # Increment distance for the next check
            distance += 0.1

        # If we didn't hit anything
        return None, None