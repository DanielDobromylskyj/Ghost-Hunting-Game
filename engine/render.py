import numpy as np
import math
import pyopencl as pycl
import pygame

from .assets import Texture2D
from .map import LoadedMap


mf = pycl.mem_flags
class OpenClContext:
    def __init__(self):
        self.context = pycl.create_some_context()
        self.queue = pycl.CommandQueue(self.context, device=None)


class Render:
    QUALITY = 0.8   # The amount textures are downscaled
    RAY_COUNT = 4000

    def __init__(self):
        if not pygame.get_init():
            pygame.init()

        self.display_size = pygame.display.get_desktop_sizes()[0]
        self.display = pygame.display.set_mode(self.display_size, pygame.SRCALPHA)

        self.font = pygame.sysfont.SysFont("monospace", 18)

        self.RAY_COUNT = round(min(self.display_size) * math.pi) * 2

        self.cl = OpenClContext()
        self.__assets = []
        self.__program = None
        self.__height_map_shape = None
        self.__height_map = None
        self.__light_map_shape = None
        self.__light_map = None
        self.__player_texture_id = None
        self.__map = None
        self.__deltas = None
        self.position = [0, 0]
        self.view_height = 0.75

        self.__load_kernels()
        self.__create_kernel_deltas()

        self.shadow_mask = np.empty(self.display_size, dtype=np.uint8)
        self.shadow_mask_buffer = pycl.Buffer(self.cl.context, mf.READ_WRITE, size=self.shadow_mask.nbytes, hostbuf=None)
        self.shadow_mask_surface = pygame.Surface(self.display_size, pygame.SRCALPHA)

    def reload_assets(self):
        """ Reload assets, including any changed settings"""
        for asset in self.__assets:
            asset.reload()

    def get_asset(self, asset_id):
        """ Gets the actual asset class by ID """
        if len(self.__assets) <= asset_id:
            raise IndexError

        return self.__assets[asset_id]

    def load_texture(self, path: str, load_pygame: bool = True, mode: str="RGB") -> int:
        """ Loads texture from the given path and returns texture id """
        self.__assets.append(
            Texture2D(path, self.QUALITY, load_pygame=load_pygame, mode=mode)
        )
        return len(self.__assets) - 1

    def load_map(self, path):
        self.__assets = [] # I think I need to clear more than just assets
        self.__map = LoadedMap(self, path)
        self.pre_compute_maps()

        self.__player_texture_id = self.load_texture("data/textures/player_place_holder.png", mode="RGBA")

    def __load_kernels(self):
        with open("data/kernel/shadow_mask.cl", "r") as f:
            self.__program = pycl.Program(self.cl.context, f.read()).build()

    def __create_kernel_deltas(self):
        angle_delta = 360 / self.RAY_COUNT
        angles = [math.radians(angle_delta * i) for i in range(self.RAY_COUNT)]

        deltas = np.array([
            (math.cos(angle), math.sin(angle))
            for angle in angles
        ], dtype=np.float32)

        self.__deltas = pycl.Buffer(self.cl.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=deltas)

    def pre_compute_maps(self):
        height_map = self.__map.compute_height_map()
        self.__height_map = pycl.Buffer(self.cl.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=height_map.data)
        self.__height_map_shape = height_map.shape

        light_map = self.__map.compute_light_map()
        self.__light_map = pycl.Buffer(self.cl.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=light_map.data)
        self.__light_map_shape = light_map.shape



    def compute_shadow_mask(self):
        pycl.enqueue_fill_buffer(self.cl.queue, self.shadow_mask_buffer, np.uint8(255), 0, self.shadow_mask.nbytes)
        max_step_count = min(self.display_size) // 2

        self.__program.mask(
            self.cl.queue, (self.RAY_COUNT,), None,
            self.shadow_mask_buffer,
            self.__height_map,
            self.__light_map,
            self.__deltas,

            np.int32(self.display_size[1]),
            np.int32(self.display_size[0]),

            np.int32(self.__height_map_shape[0]),
            np.int32(self.__height_map_shape[1]),

            np.int32(max_step_count),

            np.int32(self.position[0]),
            np.int32(self.position[1]),

            np.float32(self.view_height),
        )

        pycl.enqueue_copy(self.cl.queue, self.shadow_mask, self.shadow_mask_buffer)

        alpha_view = pygame.surfarray.pixels_alpha(self.shadow_mask_surface)
        alpha_view[:, :] = self.shadow_mask  # shapes (h, w) match

    def render_scene(self):
        self.compute_shadow_mask()

        self.display.blit(self.__map.background_img, (-self.position[1], -self.position[0]))

        for world_object in self.__map.scene.values():
            if "NORENDER" in world_object["path"]:
                continue

            texture = self.get_asset(world_object["texture_id"])
            x, y = world_object["position"]
            self.display.blit(texture.pygame_surface, (x - self.position[1], y - self.position[0]))

        self.render_self()

        self.display.blit(self.shadow_mask_surface, (0, 0))

    def render_self(self):
        self.render_player(self.display_size[0] // 2, self.display_size[1] // 2)

    def render_player(self, cx, cy):
        texture = self.get_asset(self.__player_texture_id)
        self.display.blit(texture.pygame_surface, (cx - (texture.image_width // 2), cy - (texture.image_height // 2)))

    def display_fps(self, fps):
        rect = self.font.render(f"FPS: {round(fps)}", True, (255, 0, 0))
        self.display.blit(rect, (0, 0))


