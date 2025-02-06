from pycraft.vector import Vec3, Direction
import glm, math

class Camera:
    def __init__(self, position: Vec3 = Vec3(0, 0, 0),
                       yaw: float = 0.0, pitch: float = 0.0,
                       fov=70,
                       near=0.005, far=1000,
                       aspect_ratio=16/9):
        
        self.yaw: float = yaw
        self.pitch: float = pitch
        self.fov: float = fov
        self.near: float = near
        self.far: float = far
        self.aspect_ratio: float = aspect_ratio

        self.forward: Vec3 = Direction.FORWARD.value
        self.right: Vec3 = Direction.RIGHT.value
        self.up: Vec3 = Direction.UP.value
        
        self.update_rotation()

        self.position: Vec3 = position
    
    def update_rotation(self):
        """Updates the camera's rotation based on yaw and pitch."""

        self.pitch = max(-89, min(89, self.pitch))

        pitch_rad = math.radians(self.pitch)
        yaw_rad = math.radians(self.yaw)

        self.forward = Vec3(x=math.sin(yaw_rad) * math.cos(pitch_rad),
                            y=math.sin(pitch_rad),
                            z=-math.cos(yaw_rad) * math.cos(pitch_rad)).normalize()

        # Right and up vectors are always perpendicular to the forward vector
        self.right = self.forward.cross(Direction.UP.value).normalize()
        self.up = self.right.cross(self.forward).normalize()

    def get_view_matrix(self) -> glm.mat4:
        """Returns the camera's view matrix"""
        
        return glm.lookAt(self.position.to_glm(), (self.position + self.forward).to_glm(), self.up.to_glm())

    def get_projection_matrix(self) -> glm.mat4:
        """Returns the perspective projection matrix."""
        
        return glm.perspective(math.radians(self.fov), self.aspect_ratio, self.near, self.far)