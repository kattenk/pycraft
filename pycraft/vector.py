from typing import TypeAlias
import glm, math, enum

class Axis(enum.Enum):
    """
    Represents the X, Y, and Z components/axis, we use this in the collision system
    to extract each axis from a force vector to apply them individually.
    """
    X = 0
    Y = 1
    Z = 2

class Vec3:
    """Represents a 3D vector."""

    def __init__(self, x, y=None, z=None):
        if isinstance(x, Vec3):
            self.x = x.x
            self.y = x.y
            self.z = x.z
        
        elif isinstance(x, (tuple, list)) and len(x) == 3:
            self.x, self.y, self.z = x
        
        elif y is None and z is None:
            self.x = self.y = self.z = x
        
        else:
            self.x = x
            self.y = y
            self.z = z
    
    def to_glm(self) -> glm.vec3:
        """Converts our custom Vec3 to a glm.vec3."""
        return glm.vec3(self.x, self.y, self.z)
    
    def __repr__(self):
        """Return a string representation of the Vec3."""
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def dot(self, other):
        """Calculates the dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        """Calculates the cross product."""
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def magnitude(self):
        """Return the magnitude (length) of the vector."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        """
        Vectors have direction and magnitude, "Normalization" makes the magnitude 1
        so your vector only expresses direction. it is useful when you don't want
        magnitude to interfere with your calculations.
        """
        mag = self.magnitude()

        if mag > 0:
            return Vec3(self.x / mag, self.y / mag, self.z / mag)
        
        return Vec3(0, 0, 0)
    
    def floor(self):
        return Vec3(
            math.floor(self.x),
            math.floor(self.y),
            math.floor(self.z),
        )
    
    def on_axis(self, axis: Axis): 
        """Projects the vector onto the specified axis."""
        if axis is Axis.X:
            return Vec3(self.x, 0, 0)
        elif axis is Axis.Y:
            return Vec3(0, self.y, 0)
        elif axis is Axis.Z:
            return Vec3(0, 0, self.z)
    
    def set_axis(self, axis: Axis, value: float):
        if axis is Axis.X:
            self.x = value
        elif axis is Axis.Y:
            self.y = value
        elif axis is Axis.Z:
            self.z = value
    
    def __eq__(self, other):
        """One Vec3 is equal to another if all the components are equal."""
        return isinstance(other, Vec3) and self.x == other.x and self.y == other.y and self.z == other.z
    
    def __iter__(self):
        """Makes the Vec3 unpackable like a tuple."""
        return iter((self.x, self.y, self.z))

    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __floordiv__(self, other):
        """Floor division of Vec3 by a scalar or another Vec3."""
        if isinstance(other, Vec3):
            return Vec3(self.x // other.x, self.y // other.y, self.z // other.z).floor()
        elif isinstance(other, (int, float)):
            return Vec3(self.x // other, self.y // other, self.z // other).floor()
    
    def __rmul__(self, scalar):
        return self.__mul__(scalar)

class Direction(enum.Enum):
    """
    Direction defines an easy name for all six of the axis directions,
    which can come in handy, especially in a heavily axis-aligned voxel game.
    """
    RIGHT    = Vec3(1, 0, 0)
    LEFT     = Vec3(-1, 0, 0)
    UP       = Vec3(0, 1, 0)
    DOWN     = Vec3(0, -1, 0)
    FORWARD  = Vec3(0, 0, -1)
    BACKWARD = Vec3(0, 0, 1)

class Normal(enum.Enum):
    """
    Normal is a different set of names for the Direction enum, it is meant to make code using
    directional values easier to read and understand from the perspective of a stationary object,
    instead of say, a direction of movement like Direction might be used for.
    """
    RIGHT  = Direction.RIGHT.value
    LEFT   = Direction.LEFT.value
    TOP    = Direction.UP.value
    BOTTOM = Direction.DOWN.value
    FRONT  = Direction.FORWARD.value
    BACK   = Direction.BACKWARD.value