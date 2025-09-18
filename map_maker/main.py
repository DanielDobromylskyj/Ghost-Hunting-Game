import math
import uuid

import numpy as np
import pygame
import os

from matplotlib import pyplot as plt

pygame.init()


# todo - Allow you to delete placed blocks?
# todo - Let you load maps to work on them?

"""
Controls:

Left click and drag to move texture / item
Right click and drag to pan camera around scene
Hold shift while dragging to disable grid lock
Middle Click on a texture to set it to the background
Press "m" to cycle between build modes

"""



def _load_textures_from_path(path, search=None):
    if search is None:
        search = "%TEXTURES%"

    if not pygame.get_init():
        pygame.init()

    textures = []

    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        local_search = os.path.join(search, filename)

        if os.path.isdir(filepath):
            textures.extend(_load_textures_from_path(filepath, local_search))

        if filename.endswith(".png") or filename.endswith(".jpg"):
            suffix = "." + filename.split(".")[-1]
            height = 0.0

            if "@" in filename:
                height = float(filename.split("@")[-1].removesuffix(suffix))

            textures.append((local_search, pygame.image.load(filepath), height))

    return textures

def load_textures():
    return _load_textures_from_path("../data/textures/")

def convert_to_fixed_size(textures, max_size):
    scaled = []

    for path, texture, height in textures:
        w, h = texture.get_size()

        scale = max_size / max(w, h)
        new_size = (int(w * scale), int(h * scale))

        texture = pygame.transform.smoothscale(texture, new_size)
        scaled.append(texture)

    return scaled


def round_to_closest(value, scale):
    return (value // scale) * scale


class MapMaker:
    SAVE_VERSION = 1

    def __init__(self):
        self.all_textures = load_textures()
        self.all_display_textures = convert_to_fixed_size(self.all_textures, max_size=200)
        print(f"[INFO] Loaded {len(self.all_textures)} textures")

        self.display_size = pygame.display.get_desktop_sizes()[0]
        self.display = pygame.display.set_mode(self.display_size)
        self.running = True

        self.textures_per_line = 2
        self.texture_view_scroll = 0
        self.scene = {}  # {"id": "texture_id", "position": (0, 0)}
        self.scene_position = [0, 0]
        self.selected_object = None

        self.background_texture = None

        self.grid_snap_on = True
        self.grid_snap_distance = 50   # px

        self.is_moving_scene = False
        self.font = pygame.sysfont.SysFont("monospace", 20)
        self.modes = ["object", "special"]
        self.mode = "object"

    def display_textures(self):
        start_index = self.textures_per_line * self.texture_view_scroll

        if start_index >= len(self.all_textures):
            return

        y = 10
        for texture_index in range(start_index, len(self.all_textures)):
            x = 10 if texture_index % 2 == 0 else 220

            texture = self.all_display_textures[texture_index]

            self.display.blit(
                texture, (x, y)
            )

            if texture_index % 2 != 0:
                y += 210

    def select_object(self, mouse_x, mouse_y):
        for name, obj in self.scene.items():
            texture = self.all_textures[obj['id']][1]
            x, y = obj['position']

            true_x = x + self.scene_position[0] + 430
            true_y = y + self.scene_position[1]

            if (true_x < mouse_x < true_x + texture.get_width()) and (true_y < mouse_y < true_y + texture.get_height()):
                self.selected_object = name
                return

        self.selected_object = None

    def display_scene(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        is_hovering = False
        for obj in self.scene.values():
            texture = self.all_textures[obj['id']][1]
            x, y = obj['position']

            true_x = x + self.scene_position[0] + 430
            true_y = y + self.scene_position[1]

            self.display.blit(texture, (true_x, true_y))

            if (true_x < mouse_x < true_x + texture.get_width()) and (true_y < mouse_y < true_y + texture.get_height()) and not is_hovering:
                is_hovering = True
                border_width = 2

                pygame.draw.rect(
                    self.display,
                    (40, 40, 200),
                    (true_x - border_width, true_y - border_width, texture.get_width() + border_width*2, texture.get_height() + border_width*2),
                    width=border_width,
                    border_radius=2
                )


    def display_grid(self):
        if self.grid_snap_on and self.selected_object is not None:
            x = 430 + (self.scene_position[0] % self.grid_snap_distance)
            while x < self.display_size[0]:
                pygame.draw.line(
                    self.display,
                    (120, 120, 120),
                    (x, 0), (x, self.display_size[1])
                )

                x += self.grid_snap_distance

            y = 0 + (self.scene_position[1] % self.grid_snap_distance)
            while y < self.display_size[1]:
                pygame.draw.line(
                    self.display,
                    (120, 120, 120),
                    (0, y), (self.display_size[0], y)
                )

                y += self.grid_snap_distance

    def move_object(self, name, position):
        self.scene[name]["position"] = position

    def delete_object(self, name):
        self.scene.pop(name)

    def place_object(self, texture_id, position):
        name = str(uuid.uuid4())
        self.scene[name] = {
            "position": position,
            "height": self.all_textures[texture_id][2],
            "id": texture_id
        }

        return name

    def display_sidebar(self):
        pygame.draw.rect(
            self.display,
            (40, 40, 40),
            (0, 0, 430, self.display_size[1])
        )

        rect = self.font.render(f"Mode: {self.mode}", True, (255, 255, 255))
        self.display.blit(rect, (2, self.display_size[1]-22))

        if self.mode == "object":
            self.display_textures()


    def get_pygame_texture(self, world_object):
        return self.all_textures[world_object["id"]][1]

    def get_object_shape(self, world_object):
        return self.get_pygame_texture(world_object).get_size()

    def get_size(self):
        if self.background_texture is None:
            raise Exception("Background texture is None")

        max_x, max_y = self.background_texture[1].get_size()

        for name, world_object in self.scene.items():
            pos = world_object["position"]

            w, h = self.get_object_shape(world_object)

            if max_x < w + pos[0]:
                max_x = w + pos[0]

            if max_y < h + pos[1]:
                max_y = h + pos[1]

        return max_y, max_x

    @staticmethod
    def light_intensity(distance, max_distance):
        if distance >= max_distance:
            return 0.0

        x = distance / max_distance
        return (1 - x) ** 3

    @staticmethod
    def ray_collides_with_something(height_map, start_xyh, end_xyh) -> bool:
        """ Calculates if the light ray will collide / make it. Includes height calcs"""
        x1, y1, h1 = start_xyh
        x2, y2, h2 = end_xyh


        distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 + 0.00001
        dx, dy, dh = (x2 - x1) / distance, (y2 - y1) / distance, (h2 - h1) / distance

        for i in range(0, math.ceil(distance), 1):
            cx, cy, ch = x1 + (dx * i), y1 + (dy * i), h1 + (dh * i)

            height_at_xy = height_map[round(cx)][round(cy)]

            if height_at_xy > ch:
                return True

        return False

    def compute_light_map(self, height_map):
        light_map = np.zeros(self.get_size(), dtype=np.float32)

        light_radius = 300 # Subject to Change

        for obj_index, world_object in enumerate(self.scene.values()):
            self.display_save_progress(f"Saving - Generating Light Map ({obj_index}/{len(self.scene.values())})", "This may take a while...")
            if self.all_textures[world_object["id"]][0].endswith("light_NORENDER.png"):
                w, h = self.all_textures[world_object["id"]][1].get_size()
                position = world_object["position"]
                position = (position[1] + int(h//2), position[0] + int(w//2))

                for dx in range(-light_radius, light_radius + 1):
                    for dy in range(-light_radius, light_radius + 1):
                        dist2 = dx * dx + dy * dy
                        if dist2 > light_radius * light_radius:
                            continue  # outside the circle anyway

                        distance = dist2 ** 0.5
                        intensity = self.light_intensity(distance, light_radius)

                        if intensity <= 0:
                            continue

                        index_x = position[0] + dx
                        index_y = position[1] + dy

                        if (0 < index_x < light_map.shape[0]) and (0 < index_y < light_map.shape[1]):
                            height = height_map[index_x, index_y]

                            if self.ray_collides_with_something(
                                    height_map,
                                    (*position, 0.9),
                                    (index_x, index_y, height)):
                                continue

                            light_map[index_x, index_y] += intensity
                            light_map[index_x, index_y] = min(light_map[index_x, index_y], 1.0)


        # show light map
        plt.imshow(height_map, cmap="gray")

        # Masked array: only show light where > 0
        light_masked = np.ma.masked_where(light_map <= 0, light_map)
        plt.imshow(light_masked, cmap="autumn", alpha=0.7)
        plt.show()

        return light_map

    def compute_height_map(self):
        height_map = np.zeros(self.get_size(), dtype=np.float32)

        for world_object in self.scene.values():
            if "NORENDER" in self.all_textures[world_object["id"]][0]:
                continue

            position = world_object["position"]
            position = (position[1], position[0])

            texture = self.get_pygame_texture(world_object)  # RGBA
            width, height = self.get_object_shape(world_object)
            height_value = world_object["height"]

            tex_array = pygame.surfarray.array_alpha(texture)  # shape: (w, h)
            mask = np.transpose(tex_array, (1, 0)) > 0  # shape: (h, w) (Mirrored)

            submap = height_map[position[0]:(position[0] + width), position[1]:(position[1] + height)]

            submap[mask] = height_value

        return height_map

    def display_save_progress(self, text, sub_text=""):
        self.display.fill((30, 30, 30))

        rect = pygame.sysfont.SysFont("monospace", 32).render(text, True, (255, 0, 0))

        self.display.blit(rect, (0, 0))

        rect2 = pygame.sysfont.SysFont("monospace", 16).render(sub_text, True, (255, 0, 0))
        self.display.blit(rect2, (5, rect.get_height()+5))

        pygame.display.flip()

        pygame.event.get()



    def save(self, path):
        self.display_save_progress("Saving - Generating Height Map")
        height_map = self.compute_height_map()
        self.display_save_progress("Saving - Generating Light Map (?/?)")
        light_map = self.compute_light_map(height_map)

        self.display_save_progress("Saving - Writing Objects...")
        with open(path, "wb") as f:
            f.write(self.SAVE_VERSION.to_bytes(1))

            if self.background_texture is None:
                f.write((0).to_bytes(2))
            else:
                f.write(len(self.background_texture[0]).to_bytes(2))
                f.write(self.background_texture[0].encode())

            f.write(len(self.scene.keys()).to_bytes(4))
            for name, obj in self.scene.items():
                f.write(len(name).to_bytes(2))
                f.write(name.encode())

                f.write(obj["position"][0].to_bytes(2))
                f.write(obj["position"][1].to_bytes(2))

                f.write(round(obj["height"] * 1000).to_bytes(2))

                texture_path = self.all_textures[obj["id"]][0]

                f.write(len(texture_path).to_bytes(2))
                f.write(texture_path.encode())

            self.display_save_progress("Saving - Converting Maps To Bytes...")
            height_data = height_map.tobytes()
            height_map_width, height_map_height = height_map.shape

            light_data = light_map.tobytes()
            light_map_width, light_map_height = light_map.shape

            self.display_save_progress("Saving - Writing Maps...")

            f.write(height_map_width.to_bytes(2))
            f.write(height_map_height.to_bytes(2))
            f.write(len(height_data).to_bytes(4))
            f.write(height_data)

            f.write(light_map_width.to_bytes(2))
            f.write(light_map_height.to_bytes(2))
            f.write(len(light_data).to_bytes(4))
            f.write(light_data)



        self.display_save_progress("Saving - Done!")

    def start(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.MOUSEWHEEL:
                    pos = pygame.mouse.get_pos()

                    if pos[0] < 430:
                        self.texture_view_scroll += event.y

                        if self.texture_view_scroll < 0:
                            self.texture_view_scroll = 0

                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()

                    # If left click on item
                    if event.button == 1 or event.button == 2:

                        if self.mode == "object":
                            if pos[0] < 430:
                                texture_id = ((pos[1] // 210) * 2) + (pos[0] // 215)

                                if texture_id < len(self.all_textures):
                                    if event.button == 1:
                                        self.selected_object = self.place_object(texture_id, (0, 0))
                                    else:
                                        self.background_texture = self.all_textures[texture_id]
                            else:
                                self.select_object(*pos)

                    if event.button == 3:
                        self.is_moving_scene = True

                if event.type == pygame.MOUSEMOTION:
                    pos = pygame.mouse.get_pos()

                    if self.selected_object is not None:
                        pos = (
                            pos[0] - self.scene_position[0],
                            pos[1] - self.scene_position[1]
                        )


                        if self.grid_snap_on:
                            pos = (
                                round_to_closest(pos[0] - 30, self.grid_snap_distance) + 30,
                                round_to_closest(pos[1], self.grid_snap_distance)
                            )

                        self.move_object(self.selected_object, (pos[0] - 430, pos[1]))

                    if self.is_moving_scene:
                        self.scene_position[0] += event.rel[0]
                        self.scene_position[1] += event.rel[1]


                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.mode == "object":
                        self.selected_object = None

                    if event.button == 3:
                        self.is_moving_scene = False

                if event.type == pygame.KEYDOWN:
                    char = event.unicode

                    if char == "m":
                        next_index = (self.modes.index(self.mode) + 1) % len(self.modes)
                        self.mode = self.modes[next_index]

                    if char == "s":
                        self.save("map_maker_output.bin")

            keys = pygame.key.get_pressed()

            if keys[pygame.K_LSHIFT]:
                self.grid_snap_on = False
            else:
                self.grid_snap_on = True

            self.display.fill((13, 13, 13))
            if self.background_texture:
                self.display.blit(self.background_texture[1], (self.scene_position[0] + 430, self.scene_position[1]))
                
            self.display_grid()
            self.display_scene()
            self.display_sidebar()
            pygame.display.flip()

        pygame.quit()
        exit()


if __name__ == "__main__":
    mm = MapMaker()
    mm.start()
