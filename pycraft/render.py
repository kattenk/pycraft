import moderngl
from pycraft.camera import Camera
import math, glm, struct, os
from PIL import Image
from typing import List, Dict, Tuple
from pycraft.vector import Normal as N
from pycraft.vector import Normal
from pycraft.vector import Vec3

class Renderer:
    """The Renderer class is a singleton that handles drawing the game on screen using ModernGL."""

    def __init__(self, camera: Camera, world):
        # The renderer interacts with OpenGL via ModernGL using this Context object.
        self.ctx: moderngl.Context = moderngl.create_context()

        # We enable two OpenGL features that help with visibility,
        # Depth testing makes sure triangles that are supposed to behind others don't render in front,
        # and vice versa. Back-face culling skips the rasterization of triangles that are facing the other way in screen space,
        # based on "winding order" (the order the points on the triangle appear). visible triangles will appear wound counter-clockwise.
        self.ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        # The renderer uses a "view + projection" matrix produced by the camera to transform the geometry to
        # appear as viewed from a certain point and angle in space.
        self.camera = camera

        #self.ctx.wireframe = True
        
        self.world = world

        # These are the GLSL (GL Shading Language) programs that will be compiled by the driver and then executed on the GPU,
        # the Vertex Shader runs on each vertex and transforms it according to the camera and translation matrices,
        # the Fragment shader runs on each fragment inside of the triangles produced by the vertex shader,
        # and determines it's color by sampling from a texture.
        self.program = self.ctx.program(
            vertex_shader='''
                #version 330 core
                layout(location = 0) in vec3 position;
                layout(location = 1) in vec3 texture;
                uniform mat4 camera;
                uniform mat4 translate;

                out vec3 uv_and_layer;

                void main() {
                    uv_and_layer = texture;
                    gl_Position = camera * translate * vec4(position, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330 core
                in vec3 uv_and_layer;
                out vec4 out_color;

                uniform sampler2DArray texture_array;

                void main()
                {
                    vec4 tex_color = texture(texture_array, uv_and_layer);

                    if (tex_color.a == 0.0) {
                        discard;
                    }

                    out_color = tex_color;
                }
            '''

        )

    def render(self, time_delta: float):
        """Renders the game"""

        # Clear the screen to black before each frame
        self.ctx.clear(0, 0, 0)

        # Write the camera matrix (projection * view) to the shader
        camera_matrix = self.camera.get_projection_matrix() * self.camera.get_view_matrix()
        self.program['camera'].write(camera_matrix.to_bytes())

        # Render the skybox first, before everything else
        self.render_skybox()

        # Loop through the meshes in the world and render each one
        for chunk in self.world.chunks.keys():
            for mesh in self.world.chunks[chunk].meshes:
                self.render_mesh(mesh)
        
        for mesh in self.world.overlay_meshes:
            self.render_mesh(mesh)
    
    def render_mesh(self, mesh, do_translate: bool = True):
        """
        Renders a single mesh, if the VBO and VAO for this mesh haven't been created,
        it will create them.

        Then it binds the meshes texture array, and translates it to it's position in the world.
        if 'do_translate' is False it will use the position as an offset from the camera, instead
        of the world origin. (this is used for the skybox)

        finally, it renders the mesh to the screen by calling vao.render(), which will render
        the VBO bound to it.
        """

        # If the VBO / VAO haven't been created, create them
        if mesh.data is None:
            return

        if mesh.vbo is None or mesh.vao is None:
            mesh.vbo = self.ctx.buffer(struct.pack(f'{len(mesh.data)}f', *mesh.data))
            mesh.vao = self.ctx.vertex_array(self.program, mesh.vbo, 'position', 'texture')
        
        # If the mesh's texture array isn't loaded, load it
        if mesh.textures.texture_array is None:
            mesh.textures.load(self.ctx)
        
        # Bind the texture array
        mesh.textures.texture_array.use()

        # Write the translation (position) of the mesh to the shader
        if do_translate:
            self.program['translate'].write(glm.translate(mesh.position.to_glm()).to_bytes())
        else:
            self.program['translate'].write(glm.translate(self.camera.position.to_glm() + mesh.position.to_glm()).to_bytes())

        # Render the mesh
        self.ctx.cull_face = mesh.cull_face
        mesh.vao.render(moderngl.TRIANGLES)
    
    def render_skybox(self):
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.render_mesh(self.world.skybox, do_translate=False)
        self.ctx.enable(moderngl.DEPTH_TEST)

class Mesh:
    def __init__(self, position: Vec3, data: List[Tuple[float, float, float, float, float, float]], textures, cull_face='back'):
        self.position = position
        self.data = data
        self.textures = textures
        self.cull_face = cull_face

        # This field is used by the renderer to store a reference to the
        # Vertex Buffer Object (VBO) of the mesh in video memory.
        self.vbo: moderngl.Buffer = None

        # This is a Vertex Array Object (VAO), It acts as a descriptor for the format of vertex data,
        # telling the Vertex Shader how to interpret the data you pass it.
        # all our mesh data is in the same format for simplicity: (X, Y, Z, U, V, L)
        # X, Y, Z, U, V, L
        # │  │  │  │  │  │
        # │  │  │  │  │  └──► Texture / "layer"
        # │  │  │  │  └─────► Vertical texture coordinate
        # │  │  │  └────────► Horizontal texture coordinate
        # │  │  └───────────► Z position of the vertex
        # │  └──────────────► Y position of the vertex
        # └─────────────────► X position of the vertex
        self.vao: moderngl.VertexArray = None
        # Ideally, we wouldn't create a new VertexArray (VAO) for every single mesh in the game,
        # because all our data is in the same format, so they SHOULD share the same VAO, however it is a limitation of ModernGL that
        # you can't add buffers to VAOs after they've been created. (confirmed in conversation with MGL author on Discord)
        # I could've wrote a system for that re-creates a single VAO with every new buffer but the microscopic performance benefit
        # is not worth the complexity.
    
    def discard(self):
        """This method should be called when a mesh is no longer needed in video memory"""
        if self.vao and self.vbo:
            self.vbo.release()
            self.vao.release()
    
    @staticmethod
    def generate_uniform_texture_map(texture) -> Dict[N, int]:
        return {normal: texture for normal in Normal}

    @staticmethod
    def generate_cuboid(scale: Vec3, layers: Dict[N, int], exclude_faces: List[N] = []) -> List[Tuple[float, float, float, float, float, float]]:
        """
        Used for creating cube-like meshes of various scales.
        
        the "layers" argument should be a dictionary that maps Normals to the layer index for that side,
        allowing you to apply a different texture to each side of the cuboid.
        """
        mesh_data = []

        cuboid = {
            N.BACK: [
                ((N.BACK, N.BOTTOM, N.LEFT),   (0, scale.y)),
                ((N.BACK, N.BOTTOM, N.RIGHT),  (scale.x, scale.y)),
                ((N.BACK, N.TOP, N.RIGHT),     (scale.x, 0)),

                ((N.BACK, N.BOTTOM, N.LEFT),   (0, scale.y)),
                ((N.BACK, N.TOP, N.RIGHT),     (scale.x, 0)),
                ((N.BACK, N.TOP, N.LEFT),      (0, 0))
            ],

            N.FRONT: [
                ((N.FRONT, N.TOP, N.RIGHT),    (0, 0)),
                ((N.FRONT, N.BOTTOM, N.RIGHT), (0, scale.y)),
                ((N.FRONT, N.BOTTOM, N.LEFT) , (scale.x, scale.y)),

                ((N.FRONT, N.TOP, N.LEFT),     (scale.x, 0)),
                ((N.FRONT, N.TOP, N.RIGHT),    (0, 0)),
                ((N.FRONT, N.BOTTOM, N.LEFT) , (scale.x, scale.y))
            ],

            N.RIGHT: [
                ((N.BACK, N.BOTTOM, N.RIGHT),  (0, scale.y)),
                ((N.FRONT, N.TOP, N.RIGHT),    (scale.z, 0)),
                ((N.BACK, N.TOP, N.RIGHT),     (0, 0)),

                ((N.BACK, N.BOTTOM, N.RIGHT),  (0, scale.y)),
                ((N.FRONT, N.BOTTOM, N.RIGHT), (scale.z, scale.y)),
                ((N.FRONT, N.TOP, N.RIGHT),    (scale.z, 0))
            ],

            N.LEFT: [
                ((N.BACK, N.TOP, N.LEFT),      (scale.z, 0)),
                ((N.FRONT, N.TOP, N.LEFT),     (0, 0)),
                ((N.BACK, N.BOTTOM, N.LEFT),   (scale.z, scale.y)),

                ((N.FRONT, N.TOP, N.LEFT),     (0, 0)),
                ((N.FRONT, N.BOTTOM, N.LEFT),  (0, scale.y)),
                ((N.BACK, N.BOTTOM, N.LEFT),   (scale.z, scale.y))
            ],

            N.TOP: [
                ((N.BACK, N.TOP, N.LEFT),      (0, 0)),
                ((N.FRONT, N.TOP, N.RIGHT),    (scale.x, scale.z)),
                ((N.FRONT, N.TOP, N.LEFT),     (0, scale.z)),

                ((N.BACK, N.TOP, N.LEFT),      (0, 0)),
                ((N.BACK, N.TOP, N.RIGHT),     (scale.x, 0)),
                ((N.FRONT, N.TOP, N.RIGHT),    (scale.x, scale.z)),
            ],

            N.BOTTOM: [
                ((N.FRONT, N.BOTTOM, N.LEFT),  (0, scale.z)),
                ((N.FRONT, N.BOTTOM, N.RIGHT), (scale.x, scale.z)),
                ((N.BACK, N.BOTTOM, N.LEFT),   (0, 0)),

                ((N.FRONT, N.BOTTOM, N.RIGHT), (scale.x, scale.z)),
                ((N.BACK, N.BOTTOM, N.RIGHT),  (scale.x, 0)),
                ((N.BACK, N.BOTTOM, N.LEFT),   (0, 0))
            ]
        }

        # We group the cuboid by faces and loop through them so we can apply a different layer to each face
        for face in cuboid.keys():
            if face in exclude_faces:
                continue

            for vertex in cuboid[face]:
                # Extract the position and UV tuples from the list
                position, uv = vertex
                u, v = uv
                
                # Extend the points according to the scale and a Right-handed coordinate system
                x = scale.x if N.RIGHT in position else 0
                y = scale.y if N.TOP in position else 0
                z = scale.z if N.BACK in position else 0

                # Insert the position, UV, and texture layer for this vertex into the mesh
                mesh_data.extend([x, y, z, u, v, layers[face]])
        
        return mesh_data
    
    def __eq__(self, other):
        """One Mesh is equal to another if the data is the same."""
        return isinstance(other, Mesh) and self.data == other.data

class TextureSet:
    """
    TextureSet is a wrapper around a moderngl.TextureArray object.
    """

    def __init__(self):
        self.textures = {}

        # This is used by the renderer for storing the TextureArray once this set is loaded
        self.texture_array: moderngl.TextureArray = None
    
    def add_texture(self, name: str) -> int:
        path = os.path.join("textures", f"{name}.png")

        if self.texture_array:
            raise Exception('You cannot add textures to a TextureSet after it has been loaded.')
        
        if path in self.textures.keys():
            return list(self.textures.keys()).index(path)

        self.textures[path] = len(self.textures.keys())
        return len(self.textures.keys()) - 1
    
    def load(self, context: moderngl.Context):
        if len(self.textures.keys()) == 0:
            raise Exception('TextureSet needs at least one image to load.')
        
        sample_image = Image.open(list(self.textures.keys())[0]).convert('RGBA')
        
        texture_array = context.texture_array((sample_image.width,
                                               sample_image.height,
                                               len(self.textures.keys())),
                                               components=4,
                                               dtype='f1')

        texture_data = []

        for path in list(self.textures.keys()):
            image = Image.open(path).convert('RGBA')

            if image.width != sample_image.width or image.height != sample_image.height:
                raise Exception("TextureSet cannot contain textures of varying sizes")

            image_data = list(image.getdata())

            for pixel in image_data:
                texture_data.extend(pixel)

        texture_array.write(bytes(texture_data))

        texture_array.filter = (moderngl.NEAREST, moderngl.NEAREST)
        texture_array.repeat_x = True
        texture_array.repeat_y = True

        self.texture_array = texture_array
