import numpy as np
import math
import pyopencl as pycl
import pygame

from .item import Item
from .network import Client
from .assets import Texture2D
from .map import LoadedMap
from .logger import Log
from .model import Model


mf = pycl.mem_flags
class OpenClContext:
    def __init__(self):
        self.context = pycl.create_some_context()
        self.queue = pycl.CommandQueue(self.context, device=None)


class Render:
    QUALITY = 0.8   # The amount textures are downscaled
    RAY_COUNT = 4000

    DEBUG = False

    def __init__(self, game, dont_display=False):
        self.game = game

        if not pygame.get_init():
            pygame.init()

        self.client: Client | None = None
        self.display_size = pygame.display.get_desktop_sizes()[0]

        self.dont_display = dont_display
        if not dont_display:
            self.display = pygame.display.set_mode(self.display_size, pygame.SRCALPHA)
            Log.log("Created window")

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
        self.rotation = pygame.math.Vector2(1, 0)
        self.deg_rotation = 0.0
        self.view_height = 0.75
        self.gui_scale = 1

        Log.log("Created OpenCL context")

        self.__load_kernels()
        self.__create_kernel_deltas()

        self.shadow_mask = np.empty(self.display_size, dtype=np.uint8)
        self.shadow_mask_buffer = pycl.Buffer(self.cl.context, mf.READ_WRITE, size=self.shadow_mask.nbytes, hostbuf=None)
        self.shadow_mask_surface = pygame.Surface(self.display_size, pygame.SRCALPHA)

        self.player_model = Model("data/models/player.json")
        self.inventory_texture = self.create_inventory_texture()

        self.player_models = {}
        self.is_ghost = False

    def debug_toggle(self):
        self.DEBUG = not self.DEBUG

    def create_inventory_texture(self) -> pygame.Surface:
        surface = pygame.Surface((300 * self.gui_scale + 1, 100 * self.gui_scale + 1), pygame.SRCALPHA)

        BORDER_LIGHT = (165, 165, 165)
        BORDER_DARK = (94, 94, 94)

        delta = 100 * self.gui_scale
        for i in range(3):
            x_offset = delta * i
            item = self.game.inventory[i]

            if item is not None:
                texture = pygame.transform.scale(item.get_model(), (100 * self.gui_scale, 100 * self.gui_scale))
                surface.blit(texture, (x_offset, 0))

            pygame.draw.line(
                surface,
                BORDER_LIGHT,
                (x_offset, 0),
                (x_offset, delta)
            )

            pygame.draw.line(
                surface,
                BORDER_LIGHT,
                (x_offset, 0),
                (x_offset + delta, 0)
            )

            pygame.draw.line(
                surface,
                BORDER_DARK,
                (x_offset, delta),
                (x_offset + delta, delta)
            )

            pygame.draw.line(
                surface,
                BORDER_DARK,
                (x_offset + delta, 0),
                (x_offset + delta, delta)
            )

        return surface

    def render_hud(self, deltaTime):
        self.display.blit(self.inventory_texture, (0, self.display_size[1] - self.inventory_texture.get_height()))
        self.game.tablet.tick(self.display, deltaTime)

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

        if not self.dont_display:
            self.__map = LoadedMap(self, path)
            self.pre_compute_maps()

            self.__player_texture_id = self.load_texture("data/textures/player_place_holder.png", mode="RGBA")

    def __load_kernels(self):
        with open("data/kernel/shadow_mask.cl", "r") as f:
            self.__program = pycl.Program(self.cl.context, f.read()).build()
            self.__shadow_func = self.__program.mask

        Log.log("Loaded kernels")

    def __create_kernel_deltas(self):
        angle_delta = 360 / self.RAY_COUNT
        angles = [math.radians(angle_delta * i) for i in range(self.RAY_COUNT)]

        deltas = np.array([
            (math.cos(angle), math.sin(angle))
            for angle in angles
        ], dtype=np.float32)

        self.__deltas = pycl.Buffer(self.cl.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=deltas)
        Log.log("Created kernel deltas")

    def pre_compute_maps(self):
        height_map = self.__map.compute_height_map()
        self.__height_map = pycl.Buffer(self.cl.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=height_map.data)
        self.__height_map_shape = height_map.shape
        Log.log("Computed height map")

        light_map = self.__map.compute_light_map()
        self.__light_map = pycl.Buffer(self.cl.context, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=light_map.data)
        self.__light_map_shape = light_map.shape
        Log.log("Computed light map")


    def compute_shadow_mask(self):
        pycl.enqueue_fill_buffer(self.cl.queue, self.shadow_mask_buffer, np.uint8(255), 0, self.shadow_mask.nbytes)
        max_step_count = min(self.display_size) // 2

        self.__shadow_func(
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

    def render_lobby(self):
        self.display.fill((0, 0, 0))

        if self.client.error:
            self.display.blit(
                self.font.render(f"Problem: {self.client.error}", True, (255, 255, 255)),
                (50, 50)
            )
        else:
            if not self.client.player.ready:
                self.display.blit(
                    self.font.render(f"Press the 'g' button to ready", True, (255, 255, 255)),
                    (50, 50)
                )

            else:
                self.display.blit(
                    self.font.render(f"Awaiting other players to ready (Ping: {self.client.current_ping}ms)", True, (255, 255, 255)),
                    (50, 50)
                )

    def server_ready(self):
        if not self.__height_map:
            return False

        for player in self.client.players.values():
            if not player.ready:
                return False

        if not self.client.player.ready:
            return False

        return True

    def update_network(self):
        self.client.player.position = tuple(self.position)
        self.client.player.rotation = float(self.deg_rotation)

    def update_player_orientation(self, mx, my):
        dx = (self.display_size[0] // 2) - mx
        dy = (self.display_size[1] // 2) - my

        rotation = math.atan2(dy, dx) - 1.570796
        self.player_model.set_rotation(rotation)  # Takes in radians

        self.deg_rotation = math.degrees(rotation)
        self.rotation = pygame.math.Vector2(1, 0).rotate(self.deg_rotation)

    def set_player_moving(self, is_moving: bool):
        if is_moving:
            self.player_model.set_animation("walking")
        else:
            self.player_model.set_animation("idle")

    def render_scene(self, deltaTime):
        if self.dont_display:
            return None

        self.player_model.step(deltaTime)

        if not self.server_ready():
            self.render_lobby()
            return None

        self.update_network()
        self.compute_shadow_mask()

        self.display.blit(self.__map.background_img, (-self.position[1], -self.position[0]))

        for world_object in self.__map.scene.values():
            if "NORENDER" in world_object["path"]:
                continue

            texture = self.get_asset(world_object["texture_id"])
            x, y = world_object["position"]
            self.display.blit(texture.pygame_surface, (x - self.position[1], y - self.position[0]))

        self.render_self()

        for name, player in self.client.players.items():
            if name != self.client.player.username:
                self.render_player(player)

        if not self.DEBUG:
            self.display.blit(self.shadow_mask_surface, (0, 0))

        self.render_hud(deltaTime)
        return None

    def render_self(self):
        self.render_model(self.player_model, self.display_size[0] // 2, self.display_size[1] // 2)

    def render_model(self, model: Model, cx, cy):
        texture = model.get_current()

        self.display.blit(texture, (cx - (texture.get_width() // 2), cy - (texture.get_height() // 2)))

    def render_player(self, player):
        if len(player.position) == 2:  # This networking code is old, and fucked. Royally
            player_y, player_x = player.position
            rotation = player.rotation
        else:
            player_y, player_x = player.position[0]
            rotation = player.rotation[0]

        if player.username not in self.player_models:
            self.player_models[player.username] = Model("data/models/player.json")

        texture = pygame.transform.rotate(self.player_models[player.username].get_current(), -rotation)

        # Offset so the model is centered
        player_x -= texture.get_width() // 2
        player_y -= texture.get_height() // 2

        us_x, us_y = self.position[1], self.position[0]  # x/y are flipped and its too much effort to change it

        wx = -us_x + (self.display_size[0] // 2)
        wy = -us_y + (self.display_size[1] // 2)

        self.display.blit(texture, (wx + player_x, wy + player_y))

    def display_fps(self, fps):
        if self.dont_display:
            return

        rect = self.font.render(f"FPS: {round(fps)}", True, (255, 0, 0))
        self.display.blit(rect, (0, 0))


