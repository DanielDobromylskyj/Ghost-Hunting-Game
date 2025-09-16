import uuid
import pygame
import os

pygame.init()

"""
Controls:

Left click and drag to move texture / item
Right click and drag to pan camera around scene
Hold shift while dragging to disable grid lock

"""



def _load_textures_from_path(path, search=None):
    if search is None:
        search = "%TEXTURES%"

    textures = []

    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        local_search = os.path.join(search, filename)

        if os.path.isdir(filepath):
            textures.extend(_load_textures_from_path(filepath, local_search))

        if filename.endswith(".png") or filename.endswith(".jpg"):
            textures.append((local_search, pygame.image.load(filepath)))

    return textures

def load_textures():
    return _load_textures_from_path("../data/textures/")

def convert_to_fixed_size(textures, max_size):
    scaled = []

    for path, texture in textures:
        w, h = texture.get_size()

        scale = max_size / max(w, h)
        new_size = (int(w * scale), int(h * scale))

        texture = pygame.transform.smoothscale(texture, new_size)
        scaled.append(texture)

    return scaled


def round_to_closest(value, scale):
    return (value // scale) * scale


class MapMaker:
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

        self.grid_snap_on = True
        self.grid_snap_distance = 50   # px

        self.is_moving_scene = False

    def display_textures(self):
        pygame.draw.rect(
            self.display,
            (40, 40, 40),
            (0, 0, 430, self.display_size[1])
        )

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

    def display_scene(self):
        for obj in self.scene.values():
            texture = self.all_textures[obj['id']][1]
            x, y = obj['position']

            self.display.blit(texture, (x + self.scene_position[0] + 430, y + self.scene_position[1]))


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
            "id": texture_id
        }

        return name

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
                    if pos[0] < 430 and event.button == 1:
                        texture_id = ((pos[1] // 210) * 2) + (pos[0] // 215)

                        if texture_id < len(self.all_textures):
                            self.selected_object = self.place_object(texture_id, (0, 0))

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
                    if event.button == 1:
                        self.selected_object = None

                    if event.button == 3:
                        self.is_moving_scene = False

            keys = pygame.key.get_pressed()

            if keys[pygame.K_LSHIFT]:
                self.grid_snap_on = False
            else:
                self.grid_snap_on = True


            self.display.fill((13, 13, 13))
            self.display_grid()
            self.display_scene()
            self.display_textures()
            pygame.display.flip()

        pygame.quit()
        exit()


if __name__ == "__main__":
    mm = MapMaker()
    mm.start()
