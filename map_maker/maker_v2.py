import random
import pygame
import os
import math
import tkinter as tk
from tkinter import filedialog

import project_manager

tk.Tk().withdraw()

pygame.init()


class TakeNumberInput:
    def __init__(self, display, starting_value: str | float | int | None = None,
                 allow_floats: bool = False, character_limit: int=10, width=300):
        self.__display = display
        self.__allow_floats = allow_floats
        self.__character_limit = character_limit

        self.__charset = list("-0123456789" + ("." if allow_floats else ""))

        self.__input_open = False
        self.__text = "" if starting_value is None else (str(starting_value) if isinstance(starting_value, float) and not allow_floats else str(int(starting_value)))

        self.__font = pygame.font.SysFont("Arial", 20)

        self.__padding = 15
        self.__width = width + (self.__padding * 2)
        self.__height = self.__font.get_height() + (self.__padding * 2)

        self.__surface = pygame.Surface((self.__width, self.__height), flags=pygame.SRCALPHA)
        self.__main_loop()


    def get_value(self) -> int | float | None:
        if self.__text == "":
            return None

        if self.__allow_floats:
            return float(self.__text)

        else:
            return int(self.__text)


    def __update_rendering(self):
        self.__surface = pygame.Surface((self.__width, self.__height), flags=pygame.SRCALPHA)

        pygame.draw.rect(self.__surface, (30, 30, 30), (0, 0, self.__width, self.__height), border_radius=self.__padding)

        text_rect = self.__font.render(self.__text, True, (255, 255, 255))

        self.__surface.blit(text_rect, (self.__padding, self.__padding))

    def __handle_keypress(self, event):
        if event.unicode in self.__charset:
            if len(self.__text) < self.__character_limit:
                self.__text += event.unicode

        if event.key == pygame.K_BACKSPACE:
            if len(self.__text) > 0:
                self.__text = self.__text[:-1]

        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.__input_open = False

        self.__update_rendering()


    def __main_loop(self):
        self.__update_rendering()
        self.__input_open = True

        while self.__input_open:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__input_open = False

                if event.type == pygame.KEYDOWN:
                    self.__handle_keypress(event)


            self.__display.blit(
                self.__surface,
                ((self.__display.get_width() - self.__surface.get_width()) / 2,
                 (self.__display.get_height() - self.__surface.get_height()) / 2)
            )

            pygame.display.flip()


class Door:
    has_door: bool = False
    offset: float = 0.0
    width: float = 80.0

    def __repr__(self):
        return f"Door(has_door={self.has_door}, offset={self.offset}, width={self.width})"

class Wall:
    doors: list[Door]
    is_vertical: bool = False

    def __init__(self, is_vertical: bool = False):
        self.doors = []
        self.is_vertical = is_vertical

    def __repr__(self):
        return f"Door(vertical={self.is_vertical}, doors={self.doors})"

class Room:
    room_id: int
    world_x: float
    world_y: float
    width: float
    height: float
    colour: tuple
    floor_tile: tuple[pygame.Surface, str] | None
    hiding_spot: bool = False

    rendering: pygame.Surface | None

    def __init__(self, room_id, world_x, world_y, width, height, colour):
        self.room_id = room_id
        self.world_x = world_x
        self.world_y = world_y
        self.width = width
        self.height = height
        self.colour = colour
        self.floor_tile = None
        self.rendering: None | pygame.Surface = None
        self.walls: list[Wall | None] = [Wall(), Wall(True), Wall(), Wall(True)]

    def __render_wall(self, start_x, start_y, end_x, end_y, wall: Wall):
        assert isinstance(self.rendering, pygame.Surface)
        is_vertical = start_x == end_x


        if len(wall.doors) == 0:
            pygame.draw.line(
                self.rendering,
                (255, 255, 255),
                (start_x, start_y), (end_x, end_y)
            )

        else:
            door_points = []

            for door in wall.doors:
                if is_vertical:
                    door_points.append(
                        ((start_x, start_y + door.offset), (start_x, start_y + door.offset + door.width), door.has_door)
                    )

                else:
                    door_points.append(
                        ((start_x + door.offset, start_y), (start_x + door.offset + door.width, start_y), door.has_door)
                    )

            door_points.sort(key=lambda x: x[0] if is_vertical else x[1])
            last_x = start_x
            last_y = start_y

            assert len(door_points) == len(wall.doors), "Something Fucked"

            for door_start, door_end, has_door in door_points:
                pygame.draw.line(
                    self.rendering,
                    (255, 255, 255),
                    (last_x, last_y), door_start
                )

                if has_door:
                    pygame.draw.line(
                        self.rendering,
                        (150, 150, 150),
                        door_start, door_end
                    )

                last_x, last_y = door_end

            if last_x != end_x or last_y != end_y:
                pygame.draw.line(
                    self.rendering,
                    (255, 255, 255),
                    (last_x, last_y), (end_x, end_y)
                )


    def render_room(self):
        self.rendering: pygame.Surface = pygame.Surface((self.width, self.height), flags=pygame.SRCALPHA).convert_alpha()
        assert isinstance(self.rendering, pygame.Surface)

        font = pygame.font.SysFont("Arial", 20)
        if self.floor_tile:
            for x in range(0, math.ceil(self.width / self.floor_tile[0].get_width())+1):
                for y in range(0, math.ceil(self.height / self.floor_tile[0].get_height())+1):
                    self.rendering.blit(self.floor_tile[0], (x * self.floor_tile[0].get_width(),
                                                               y * self.floor_tile[0].get_height()))

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((*self.colour, 80))
        self.rendering.blit(overlay, (0, 0))


        rect = font.render(str(self.room_id), True, self.colour)
        self.rendering.blit(rect, (5, 5))

        pygame.draw.rect(
            self.rendering,
            self.colour,
            (0, 0, self.width, self.height),
            width=2
        )

        if self.hiding_spot:
            for start_x in range(0, int(self.width) * 2, 20):
                offset = 0 if start_x % 40 == 0 else -20
                ray_x, ray_y = start_x - offset + 10, offset

                visible = False
                while ray_x > 0 and ray_y < self.height:
                    next_x, next_y = ray_x - 20, ray_y + 20

                    if visible:
                        pygame.draw.line(
                            self.rendering,
                            self.colour,
                            (ray_x, ray_y),
                            (next_x, next_y),
                            width = 2
                        )

                    visible = not visible

                    ray_x, ray_y = next_x, next_y


        if self.walls[0] is not None:
            self.__render_wall(0, 0, self.width-1, 0, self.walls[0])  # NOQA

        if self.walls[1] is not None:
            self.__render_wall(self.width-1, 0, self.width-1, self.height-1, self.walls[1])  # NOQA

        if self.walls[2] is not None:
            self.__render_wall(0, self.height-1, self.width-1, self.height-1, self.walls[2])  # NOQA

        if self.walls[3] is not None:
            self.__render_wall(0, 0, 0, self.height-1, self.walls[3])  # NOQA



class App:
    def __init__(self):
        self.display = pygame.display.set_mode(pygame.display.get_desktop_sizes()[0])
        self.__display_loading()
        self.running = False

        self.layers = ["rooms"]
        self.editing_modes = ["rooms", "walls", "objects"]
        self.editing_layer = "rooms"

        self.tool_tips = {
            "rooms": ("Shift + Left-Click + Drag -> Creates a new room over the selected area",
                      "Left-Click -> Open the properties of a room (and its size)"),
            "walls": ("Left-Click (On Room) -> Select a room to edit",
                      "Left-Click (On '+' Icon) -> Create a new doorway",
                      "Left-Click + Drag (On Door Arrow) -> Relocate a doorway to a new location",
                      "Right-Click (On Door Arrow) -> Open doorway config for a given doorway"),
            "objects": ("Left-Click + Drag -> Move Objects around",
                        "N -> Create new object",
                        "G -> Toggle Grid Snap")
        }

        self.camera_position = [0, 0]
        self.camera_scale = 1

        self.zoom_map = [0.25, 0.5, 1, 1.5, 2.5, 5, 10, 20]
        self.zoom = self.zoom_map.index(1)

        self.textures_loaded = 0
        self.textures = self.__load_textures("../data/textures")
        print(f"Found and loaded {self.textures_loaded} textures!")


        self.room_layout: list[Room] = [Room(1, 0, 0, 500, 300, (150, 10, 10)),
                                        Room(2, 500, 200, 200, 100, (10, 10, 150))]
        self.object_layout: list = []

        self.object_layer_surface = None
        self.dragging_object = None
        self.dragging_object_loc = [0, 0]
        self.dragging_object_start_loc = [0, 0]
        self.object_grid_snap = True
        self.create_object_layer()

        self.grid_snap = 25
        self.selected_room = None
        self.selected_room_cache = None

        self.font = pygame.font.SysFont("Arial", 20)
        self.text_sizes = {}

        self.dragging = False
        self.mouse_held = False
        self.dragging_start = (0, 0)

        self.wall_door_creation_locations = []
        self.wall_door_dragging = None
        self.wall_drag_start_offset = None
        self.wall_door_config_surf = None
        self.wall_door_config_door = None

        # Testing data only:
        self.room_layout[0].walls[1].doors = [Door(), Door()]       # NOQA

        self.room_layout[0].walls[1].doors[0].offset = 210.0        # NOQA

        self.room_layout[0].walls[1].doors[1].offset = 150.0        # NOQA
        self.room_layout[0].walls[1].doors[1].width = 50.0          # NOQA
        self.room_layout[0].walls[1].doors[1].has_door = True       # NOQA

        # End of test data

        self.undo_log = []
        self.redo_log = []

    def inc_edit_mode(self):
        new_index = (self.editing_modes.index(self.editing_layer) + 1) % len(self.editing_modes)
        self.set_editing_mode(self.editing_modes[new_index])

    def set_editing_mode(self, mode: str):
        assert mode in self.editing_modes
        self.editing_layer = mode


    def __load_textures(self, path, texture_data=None) -> dict:
        if texture_data is None: texture_data = {}

        for filename in os.listdir(path):
            if os.path.isfile(os.path.join(path, filename)):
                if filename.endswith(".png"):
                    texture_data[filename] = pygame.image.load(os.path.join(path, filename)).convert_alpha()
                    self.textures_loaded += 1

            elif os.path.isdir(os.path.join(path, filename)):
                internals: dict = self.__load_textures(os.path.join(path, filename))
                texture_data[filename] = internals

        return texture_data

    def __world_space_to_camera(self, x, y):
        return (x + self.camera_position[0]) * self.camera_scale, (y + self.camera_position[1]) * self.camera_scale

    def __camera_to_world_space(self, x, y):
        return (x / self.camera_scale) - self.camera_position[0], (y / self.camera_scale) - self.camera_position[1]

    def __display_loading(self):
        font = pygame.font.SysFont("Arial", 40)
        rect = font.render("Loading...", True, (255,255,255))
        self.display.blit(rect, ((self.display.get_width() - rect.get_width()) / 2, (self.display.get_height() - rect.get_height()) / 2))
        pygame.display.flip()

    def redraw_all_rooms(self):
        self.__render_rooms()
        self.create_object_layer()

    def __render_rooms(self):
        for room in self.room_layout:
            if room.rendering is None:
                room.render_room()

            assert isinstance(room.rendering, pygame.Surface)
            self.display.blit(
                pygame.transform.scale_by(room.rendering, self.camera_scale),
                self.__world_space_to_camera(room.world_x, room.world_y)
            )

            if self.editing_layer == "walls" and room != self.selected_room and self.selected_room is not None:
                assert room.rendering is not None
                blanking_surface = pygame.Surface(room.rendering.get_size(), pygame.SRCALPHA)
                blanking_surface.fill((50, 50, 50, 150))

                self.display.blit(
                    pygame.transform.scale_by(blanking_surface, self.camera_scale),
                    self.__world_space_to_camera(room.world_x, room.world_y)
                )


    def __display_tool_tips(self):
        if self.editing_layer in self.tool_tips:
            tips = self.tool_tips[self.editing_layer]
            x = 5
            y = 35
            for i, tip in enumerate(tips):
                rect = self.font.render(tip, True, (255,255,255))
                self.display.blit(rect, (x, y))
                y += rect.get_height() + 2

    def __snap_point_to_grid(self, world_x, world_y):
        snapped_x = round(world_x / self.grid_snap) * self.grid_snap
        snapped_y = round(world_y / self.grid_snap) * self.grid_snap

        return snapped_x, snapped_y

    def create_new_room(self, mouse_x, mouse_y):
        start_x, start_y = self.dragging_start

        snapped_x, snapped_y = self.__snap_point_to_grid(
            *self.__camera_to_world_space(mouse_x, mouse_y)
        )

        w, h = snapped_x - start_x, snapped_y - start_y

        if w < 0:
            start_x += w
            w *= -1

        if h < 0:
            start_y += h
            h *= -1

        if w == 0 or h == 0:
            return

        new_room_id = len(self.room_layout) + 1
        colour = (random.randint(10, 255), random.randint(10, 255), random.randint(10, 255))
        self.room_layout.append(Room(new_room_id, start_x, start_y, w, h, colour))
        self.add_undo_step("create-room", new_room_id)

    def render_door_creation_points(self):
        if self.selected_room is None:
            self.wall_door_creation_locations = []
            return

        add_icon = pygame.Surface((9, 9), pygame.SRCALPHA)
        pygame.draw.line(add_icon, (242, 221, 31), (0, 4), (8, 4), width=3)
        pygame.draw.line(add_icon, (242, 221, 31), (4, 0), (4, 8), width=3)

        door_icon_up = pygame.Surface((9, 9), pygame.SRCALPHA)
        pygame.draw.line(door_icon_up, (42, 249, 242), (4, 0), (4, 8), width=3)
        pygame.draw.line(door_icon_up, (42, 249, 242), (4, 0), (0, 4), width=3)
        pygame.draw.line(door_icon_up, (42, 249, 242), (4, 0), (8, 4), width=3)

        self.wall_door_creation_locations = [
            (0, add_icon, (self.selected_room.world_x + (self.selected_room.width // 2),
                        self.selected_room.world_y - 10), "new"),

            (1, add_icon, (self.selected_room.world_x + self.selected_room.width + 1,
                        self.selected_room.world_y + (self.selected_room.height // 2)), "new"),

            (2, add_icon, (self.selected_room.world_x + (self.selected_room.width // 2),
                                                     self.selected_room.world_y + self.selected_room.height + 1), "new"),

            (3, add_icon, (self.selected_room.world_x - 10,
                                                     self.selected_room.world_y + (self.selected_room.height // 2)), "new")
        ]

        sl = self.selected_room
        segments = [
            ((sl.world_x, sl.world_y), False),
            ((sl.world_x + sl.width, sl.world_y), True),
            ((sl.world_x, sl.world_y + sl.height), False),
            ((sl.world_x, sl.world_y), True)
        ]
        offset_lookup = [ (0, -11), (2, 0), (0, 1), (-11, 0) ]

        for i, ((start_x, start_y), is_vertical) in enumerate(segments):
            if self.selected_room.walls[i] is None:
                continue

            for j, door in enumerate(self.selected_room.walls[i].doors):
                door_x1 = start_x + (0 if is_vertical else door.offset)
                door_y1 = start_y + (door.offset if is_vertical else 0)

                dx = (0 if is_vertical else door.width / 2) + offset_lookup[i][0]
                dy = (door.width / 2 if is_vertical else 0) + offset_lookup[i][1]

                self.wall_door_creation_locations.append(
                    (                                # NOQA
                        (i, j),
                        pygame.transform.rotate(door_icon_up, 90*i + (0 if is_vertical else 180)),
                        (door_x1 + dx, door_y1 + dy),
                        "door")
                )

        # Remove any NoneType wall icons
        for x in self.wall_door_creation_locations:
            if x[0] is None:
                self.wall_door_creation_locations.remove(x)

    def select_room(self, mouse_x, mouse_y, dont_render=False):
        self.selected_room = None
        self.selected_room_cache = None
        self.wall_door_config_surf = None

        world_x, world_y = self.__camera_to_world_space(mouse_x, mouse_y)

        for room in self.room_layout:
            if (room.world_x < world_x < room.world_x + room.width and
                room.world_y < world_y < room.world_y + room.height):

                self.selected_room = room
                break


        if self.editing_layer == "walls":
            self.render_door_creation_points()

        if self.selected_room and not dont_render:
            if self.selected_room.rendering is None:
                self.selected_room.render_room()

            self.selected_room_cache = pygame.Surface((400, self.display.get_height()))
            self.selected_room_cache.fill((30, 30, 30))

            pygame.draw.rect(
                self.selected_room_cache,
                (10, 10, 10),
                (20, 50, 360, 200),
                border_radius=10
            )

            scale_factor = min(340 / self.selected_room.width, 180 / self.selected_room.height)

            assert isinstance(self.selected_room.rendering, pygame.Surface)
            preview = pygame.transform.scale_by(self.selected_room.rendering, scale_factor)

            self.selected_room_cache.blit(preview, (30, 60))

            title_rect = self.font.render(f"Editing Room {self.selected_room.room_id}", True, (255,255,255))
            self.selected_room_cache.blit(title_rect, (10, 10))

            change_tile_rect = self.font.render("Change Floor", True, (255,255,255))
            self.text_sizes["Change Floor"] = change_tile_rect.get_size()

            y = 300
            pygame.draw.rect(
                self.selected_room_cache,
                (20, 20, 20),
                (10, y-5, change_tile_rect.get_width() + 10, change_tile_rect.get_height() + 10),
                border_radius=5
            )

            self.selected_room_cache.blit(change_tile_rect, (15, y))


            toggle_hiding_spot = self.font.render("Toggle Hiding Spot", True, (255,255,255))
            self.text_sizes["Toggle Hiding Spot"] = toggle_hiding_spot.get_size()

            y = 350
            pygame.draw.rect(
                self.selected_room_cache,
                (20, 20, 20),
                (10, y-5, toggle_hiding_spot.get_width() + 10, toggle_hiding_spot.get_height() + 10),
                border_radius=5
            )

            self.selected_room_cache.blit(toggle_hiding_spot, (15, y))

    def add_undo_step(self, undo_type: str, data):
        self.undo_log.append((undo_type, data))
        self.redo_log = []

    def undo(self):
        if len(self.undo_log) == 0:
            return

        event, data = self.undo_log.pop(-1)

        if event == "create-room":
            room_id = data

            actual_room = None
            for room in self.room_layout:
                if room.room_id == room_id:
                    actual_room = room
                    break

            assert actual_room is not None, "Invalid room id in undo statement"
            self.room_layout.remove(actual_room)
            self.redo_log.append(("create-room", actual_room))

        elif event == "room-change_tile":
            room, old, new = data

            room.floor_tile = old

            room.render_room()

            self.redo_log.append(("room-change_tile", (room, old, new)))

        elif event == "new-door":
            room, doors, door_to_remove = data

            i = doors.index(door_to_remove)
            doors.pop(i)

            room.render_room()
            self.render_door_creation_points()

            self.redo_log.append(("new-door", (room, doors, door_to_remove)))

        elif event == "move-door":
            # self.selected_room.walls[wall_index], door_index, self.wall_drag_start_offset, current_offset
            room, wall, door_index, old_offset, new_offset = data
            wall.doors[door_index].offset = old_offset

            room.render_room()
            self.render_door_creation_points()

            self.redo_log.append(("move-door", (room, wall, door_index, old_offset, new_offset)))

        elif event == "door_config-delete":
            room, door, wall_index, door_index = data

            room.walls[wall_index].doors.insert(door_index, door)

            room.render_room()
            self.render_door_creation_points()

            self.redo_log.append(("door_config-delete", (room, door, wall_index, door_index)))

        elif event == "door_config-visable":
            room, door, starting_state, new_state = data

            door.has_door = starting_state

            room.render_room()
            self.render_door_creation_points()

            self.redo_log.append(("door_config-visable", (room, door, starting_state, new_state)))

        elif event == "door_config-width":
            room, door, starting_width, end_width = data

            door.width = starting_width

            room.render_room()
            self.render_door_creation_points()

            self.redo_log.append(("door_config-width", (room, door, starting_width, end_width)))

        elif event == "toggle_hiding_spot":
            room, old, new = data
            room.hiding_spot = old
            room.render_room()

            self.redo_log.append(("toggle_hiding_spot", (room, old, new)))

        elif event == "new-object":
            room, index, obj = data

            self.object_layout.pop(index)

            self.create_object_layer()

            self.redo_log.append(("new-object", (room, index, obj)))

        elif event == "object-move":
            index, start, end = data

            print(index, start, end)

            self.object_layout[index][1][0] = start[0]
            self.object_layout[index][1][1] = start[1]

            self.create_object_layer()

            self.redo_log.append(("object-move", (index, start, end)))

        else:
            print("Unknown undo event:", event)


    def redo(self):
        if len(self.redo_log) == 0:
            return

        event, data = self.redo_log.pop(-1)
        if event == "create-room":
            self.room_layout.append(data)
            self.undo_log.append(("create-room", data.room_id))

        elif event == "room-change_tile":
            room, old, new = data

            room.floor_tile = new

            room.render_room()

            self.undo_log.append(("room-change_tile", (room, old, new)))

        elif event == "new-door":
            room, doors, door_to_remove = data

            doors.append(door_to_remove)

            room.render_room()
            self.render_door_creation_points()

            self.undo_log.append(("new-door", (room, doors, door_to_remove)))

        elif event == "move-door":
            room, wall, door_index, old_offset, new_offset = data

            wall.doors[door_index].offset = new_offset

            room.render_room()
            self.render_door_creation_points()

            self.undo_log.append(("move-door", (room, wall, door_index, old_offset, new_offset)))

        elif event == "door_config-delete":
            room, door, wall_index, door_index = data

            room.walls[wall_index].doors.remove(door)

            room.render_room()
            self.render_door_creation_points()

            self.undo_log.append(("door_config-delete", (room, door, wall_index, door_index)))

        elif event == "door_config-visable":
            room, door, starting_state, new_state = data

            door.has_door = new_state

            room.render_room()
            self.render_door_creation_points()

            self.undo_log.append(("door_config-visable", (room, door, starting_state, new_state)))

        elif event == "door_config-width":
            room, door, starting_width, end_width = data

            door.width = end_width

            room.render_room()
            self.render_door_creation_points()

            self.undo_log.append(("door_config-width", (room, door, starting_width, end_width)))

        elif event == "toggle_hiding_spot":
            room, old, new = data
            room.hiding_spot = new
            room.render_room()

            self.undo_log.append(("toggle_hiding_spot-width", (room, old, new)))

        elif event == "new-object":
            room, index, obj = data

            self.object_layout.insert(index, obj)

            self.create_object_layer()

            self.redo_log.append(("new-object", (room, index, obj)))

        elif event == "object-move":
            index, start, end = data

            self.object_layout[index][1][0] = end[0]
            self.object_layout[index][1][1] = end[1]

            self.create_object_layer()

            self.redo_log.append(("object-move", (index, start, end)))

        else:
            print("Unknown redo event:", event)


    def clicked_on_room_preview(self, x, y):
        if 10 < x < 10 + self.text_sizes["Change Floor"][0]:
            if 300 < y < 300 + self.text_sizes["Change Floor"][1]:
                path = filedialog.askopenfilename(defaultextension="png", filetypes=[("PNG files", "*.png")])

                try:
                    img = pygame.image.load(path).convert_alpha()
                    new_tile = [img, path]
                    old_tile = self.selected_room.floor_tile
                    self.selected_room.floor_tile = new_tile

                    self.add_undo_step("room-change_tile", (self.selected_room, old_tile, new_tile))
                    self.selected_room.render_room()
                except:  # NOQA
                    pass

        if 10 < x < 10 + self.text_sizes["Toggle Hiding Spot"][0]:
            if 350 < y < 350 + self.text_sizes["Toggle Hiding Spot"][1]:
                old = self.selected_room.hiding_spot
                new = not old

                self.selected_room.hiding_spot = new

                self.selected_room.render_room()
                self.undo_log.append(("toggle_hiding_spot", (self.selected_room, old, new)))


    def clicked_on_doorway_preview(self, x, y):
        if self.selected_room is None:
            print("[WARNING] No room selected")
            return

        if 10 < x < 10 + self.text_sizes["Set Door Width"][0]:
            if 50 < y < 50 + self.text_sizes["Set Door Width"][1]:
                starting_width = self.wall_door_config_door.width
                new_width = TakeNumberInput(self.display, int(starting_width)).get_value()

                if new_width is not None:
                    self.wall_door_config_door.width = new_width
                    self.add_undo_step("door_config-width", (self.selected_room, self.wall_door_config_door, starting_width, new_width))

                    self.selected_room.render_room()
                    self.render_door_creation_points()

        if 10 < x < 10 + self.text_sizes["Toggle Door"][0]:
            if 100 < y < 100 + self.text_sizes["Toggle Door"][1]:
                starting_state = self.wall_door_config_door.has_door
                new_state = not starting_state

                self.wall_door_config_door.has_door = new_state
                self.add_undo_step("door_config-visable", (self.selected_room, self.wall_door_config_door, starting_state, new_state))

                self.selected_room.render_room()
                self.render_door_creation_points()

        if 10 < x < 10 + self.text_sizes["Delete Door"][0]:
            if 150 < y < 150 + self.text_sizes["Delete Door"][1]:
                for i, wall in enumerate(self.selected_room.walls):
                    if wall is None:
                        continue

                    for j, door in enumerate(wall.doors):
                        if door == self.wall_door_config_door:
                            self.selected_room.walls[i].doors.pop(j)
                            self.add_undo_step("door_config-delete", (self.selected_room, self.wall_door_config_door, i, j))

                self.selected_room.render_room()
                self.render_door_creation_points()

    def open_doorway_config(self, doorway_data):
        wall_index, door_index = doorway_data
        self.wall_door_config_door = self.selected_room.walls[wall_index].doors[door_index]

        self.wall_door_config_surf = pygame.Surface((400, self.display.get_height()))
        config_screen = self.wall_door_config_surf

        config_screen.fill((30, 30, 30))

        change_width_rect = self.font.render("Set Door Width", True, (255, 255, 255))
        self.text_sizes["Set Door Width"] = change_width_rect.get_size()

        y = 50
        pygame.draw.rect(
            config_screen,
            (20, 20, 20),
            (10, y - 5, change_width_rect.get_width() + 10, change_width_rect.get_height() + 10),
            border_radius=5
        )

        config_screen.blit(change_width_rect, (15, y))

        toggle_door_rect = self.font.render("Toggle Door", True, (255, 255, 255))
        self.text_sizes["Toggle Door"] = toggle_door_rect.get_size()

        y = 100
        pygame.draw.rect(
            config_screen,
            (20, 20, 20),
            (10, y - 5, toggle_door_rect.get_width() + 10, toggle_door_rect.get_height() + 10),
            border_radius=5
        )

        config_screen.blit(toggle_door_rect, (15, y))

        remove_door_rect = self.font.render("Delete Door", True, (255, 255, 255))
        self.text_sizes["Delete Door"] = remove_door_rect.get_size()

        y = 150
        pygame.draw.rect(
            config_screen,
            (20, 20, 20),
            (10, y - 5, remove_door_rect.get_width() + 10, remove_door_rect.get_height() + 10),
            border_radius=5
        )

        config_screen.blit(remove_door_rect, (15, y))

    def create_object_layer(self):
        self.object_layer_surface = pygame.Surface(self.display.get_size(), pygame.SRCALPHA)

        for i, (surface, pos, path) in enumerate(self.object_layout):
            if i == self.dragging_object:
                surface = pygame.transform.scale_by(surface, self.camera_scale).convert_alpha()
                mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                mask.fill((0, 0, 0, 100))

                surface.blit(mask, (0, 0))

                self.object_layer_surface.blit(
                    surface, self.__world_space_to_camera(*pos)
                )
            else:
                self.object_layer_surface.blit(
                    pygame.transform.scale_by(surface, self.camera_scale), self.__world_space_to_camera(*pos)
                )

    def add_object(self):
        path = filedialog.askopenfilename(defaultextension="png", filetypes=[("PNG files", "*.png")])

        try:
            pos = [0, 0]

            #if self.selected_room:
            #    pos = [self.selected_room.world_x, self.selected_room.world_y]

            img = pygame.image.load(path).convert_alpha()
            self.object_layout.append((img, pos, path))

            self.add_undo_step("new-object", (self.selected_room, len(self.object_layout) - 1, (img, pos, path)))
            self.create_object_layer()
        except:  # NOQA
            pass


    def print_log(self):
        print("> Map Maker Log <")
        print("Undo History")
        for event, data in self.undo_log:
            print(f"{event} | {data}")

        print("Redo History")
        for event, data in self.redo_log:
            print(f"{event} | {data}")

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension="project", filetypes=[("Map Maker Project File", "*.project")])
        if not path: return

        project_manager.save_project(path, self.room_layout, self.object_layout)
        print("Save Completed!")

    def load(self):
        path = filedialog.askopenfilename(defaultextension="project", filetypes=[("Map Maker Project File", "*.project")])
        if not path: return

        self.room_layout, self.object_layout = project_manager.load_project(path)
        self.redraw_all_rooms()
        print("Load Completed!")

    def select_object(self, mx, my):
        wx, wy = self.__camera_to_world_space(mx, my)
        # Don't exit early, we want the top most object
        for i, (img, pos, path) in enumerate(self.object_layout):
            if pos[0] < wx < pos[0] + img.get_width():
                if pos[1] < wy < pos[1] + img.get_height():
                    self.dragging_object = i
                    self.dragging_object_loc = pos
                    self.dragging_object_start_loc = (*pos,)  # Copy the tuple (store it for later)

        self.create_object_layer()

    def run(self):
        self.running = True

        ignore_reselect = False
        while self.running:
            mouse_buttons_pressed = pygame.mouse.get_pressed()
            mouse_x, mouse_y = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        self.inc_edit_mode()

                    if event.key == pygame.K_z:
                        if event.mod & pygame.KMOD_SHIFT and event.mod & pygame.KMOD_CTRL:
                            self.redo()

                        elif event.mod & pygame.KMOD_CTRL:
                            self.undo()

                    if event.key == pygame.K_s:
                        if event.mod & pygame.KMOD_CTRL:
                            self.save()

                    if event.key == pygame.K_l:
                        if event.mod & pygame.KMOD_CTRL:
                            self.load()
                        else:
                            self.print_log()

                    if event.key == pygame.K_n:
                        if self.editing_layer == "objects":
                            self.add_object()

                    if event.key == pygame.K_g:
                        if self.editing_layer == "objects":
                            self.object_grid_snap = not self.object_grid_snap

                if event.type == pygame.MOUSEMOTION:
                    if self.mouse_held and not self.dragging:
                        camera_space = self.__world_space_to_camera(*self.dragging_start)

                        if abs(event.pos[0] - camera_space[0]) > 40 or abs(event.pos[0] - camera_space   [1]) > 40:
                            self.dragging = True

                    if mouse_buttons_pressed[2]:
                        self.camera_position[0] += event.rel[0] * (1 / self.camera_scale)
                        self.camera_position[1] += event.rel[1] * (1 / self.camera_scale)

                        self.create_object_layer()  # Update the objects

                    #if self.dragging:
                    else:
                        if self.editing_layer == "walls":
                            if self.wall_door_dragging is not None:
                                wall_index, door_index = self.wall_door_dragging
                                wall = self.selected_room.walls[wall_index]
                                dx, dy = event.rel

                                delta = dy  if wall.is_vertical else dx
                                scaled_delta = (delta * (1 / self.camera_scale))
                                wall.doors[door_index].offset += scaled_delta

                                self.selected_room.render_room()
                                self.render_door_creation_points()

                        if self.dragging and self.editing_layer == "objects" and self.dragging_object is not None:
                            self.dragging_object_loc[0] += event.rel[0] * (1 / self.camera_scale)
                            self.dragging_object_loc[1] += event.rel[1] * (1 / self.camera_scale)


                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if (self.editing_layer == "rooms" and
                            self.selected_room is not None and
                            mouse_x > self.display.get_width() - 400):
                            self.clicked_on_room_preview(mouse_x - (self.display.get_width() - 400), mouse_y)

                        if (self.editing_layer == "walls" and
                            self.wall_door_config_surf is not None and
                            mouse_x > self.display.get_width() - 400):
                            self.clicked_on_doorway_preview(mouse_x - (self.display.get_width() - 400), mouse_y)

                        else:
                            self.mouse_held = True
                            self.dragging_start = self.__snap_point_to_grid(*self.__camera_to_world_space(*event.pos))

                            if self.editing_layer == "rooms":
                                self.select_room(mouse_x, mouse_y)

                            if self.editing_layer == "objects":
                                self.select_object(mouse_x, mouse_y)

                    if event.button in (1, 3) and self.selected_room is not None:
                        if self.editing_layer == "walls":
                            if self.selected_room is not None:
                                mw_x, mw_y = self.__camera_to_world_space(mouse_x, mouse_y)
                                for data, icon, xy, name in self.wall_door_creation_locations:
                                    if xy[0] < mw_x < xy[0] + icon.get_width() and xy[1] < mw_y < xy[1] + icon.get_height():
                                        if name == "door":
                                            if event.button == 1:
                                                wall_index, door_index = data
                                                self.wall_door_dragging = (wall_index, door_index)
                                                self.wall_drag_start_offset = self.selected_room.walls[wall_index].doors[door_index].offset
                                            else:
                                                self.open_doorway_config(data)

                                        elif name == "new":
                                            if event.button == 1:
                                                new_door = Door()
                                                self.selected_room.walls[data].doors.append(new_door)
                                                self.add_undo_step("new-door", (self.selected_room, self.selected_room.walls[data].doors, new_door))

                                                self.selected_room.render_room()
                                                self.render_door_creation_points()

                                                ignore_reselect = True

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.wall_door_dragging is not None:
                            wall_index, door_index = self.wall_door_dragging
                            current_offset = self.selected_room.walls[wall_index].doors[door_index].offset
                            self.add_undo_step("move-door", (self.selected_room, self.selected_room.walls[wall_index], door_index, self.wall_drag_start_offset, current_offset))


                        if self.dragging:
                            if self.editing_layer == "rooms":
                                self.create_new_room(mouse_x, mouse_y)

                            if self.editing_layer == "objects":
                                if self.dragging_object is not None:
                                    if self.object_grid_snap:
                                        self.dragging_object_loc = self.__snap_point_to_grid(*self.dragging_object_loc)

                                    self.add_undo_step("object-move", (
                                        self.dragging_object, (self.dragging_object_start_loc[0], self.dragging_object_start_loc[1]),
                                        (self.dragging_object_loc[0], self.dragging_object_loc[1])
                                    ))


                                    self.object_layout[self.dragging_object][1][0] = self.dragging_object_loc[0]
                                    self.object_layout[self.dragging_object][1][1] = self.dragging_object_loc[1]
                                    self.dragging_object = None
                                    self.create_object_layer()

                        else:
                            if self.editing_layer == "walls":
                                if not ignore_reselect:
                                    self.select_room(mouse_x, mouse_y, dont_render=True)
                                else:
                                    ignore_reselect = False

                        self.wall_door_dragging = None
                        self.mouse_held = False
                        self.dragging = False

                if event.type == pygame.MOUSEWHEEL:
                    # World coordinate under mouse BEFORE zoom
                    world_x, world_y = self.__camera_to_world_space(mouse_x, mouse_y)

                    # Apply zoom
                    self.zoom = max(0, min(self.zoom + event.y, len(self.zoom_map) - 1))
                    self.camera_scale = self.zoom_map[self.zoom]

                    # Where that world point appears AFTER zoom
                    new_screen_x, new_screen_y = self.__world_space_to_camera(world_x, world_y)

                    # Move camera so the point stays under the cursor, Now we have a nice zoom unlike some of my projects
                    self.camera_position[0] += (mouse_x - new_screen_x) / self.camera_scale
                    self.camera_position[1] += (mouse_y - new_screen_y) / self.camera_scale

                    self.create_object_layer()  # Update the objects

            self.display.fill((10, 10, 10))

            self.__render_rooms()

            if self.editing_layer == "rooms":
                if self.dragging:
                    start_x, start_y = self.__world_space_to_camera(*self.dragging_start)

                    snapped_x, snapped_y = self.__world_space_to_camera(
                        *self.__snap_point_to_grid(
                            *self.__camera_to_world_space(mouse_x, mouse_y)
                        )
                    )
                    w, h = snapped_x - start_x, snapped_y - start_y

                    if w < 0:
                        start_x += w
                        w *= -1

                    if h < 0:
                        start_y += h
                        h *= -1

                    pygame.draw.rect(
                        self.display,
                        (10, 10, 150, 80),
                        (start_x, start_y, w, h)
                    )

                if self.selected_room_cache is not None:
                    self.display.blit(
                        self.selected_room_cache,
                        (self.display.get_width() - self.selected_room_cache.get_width(), 0)
                    )

            if self.editing_layer == "walls":
                if self.selected_room:
                    for wall, icon, xy, _ in self.wall_door_creation_locations:
                        self.display.blit(
                            icon, self.__world_space_to_camera(*xy)
                        )

                    if self.wall_door_config_surf:
                        self.display.blit(self.wall_door_config_surf, (self.display.get_width() - 400, 0))

            if self.dragging and self.editing_layer == "objects" and self.dragging_object is not None:
                img, _, _ = self.object_layout[self.dragging_object]

                pos = self.dragging_object_loc

                if self.object_grid_snap:
                    pos = self.__snap_point_to_grid(*pos)

                self.display.blit(img, self.__world_space_to_camera(*pos))


            self.display.blit(self.object_layer_surface, (0, 0))

            mode_rect = self.font.render(f"Editing: {self.editing_layer}", True, (255,255,255))
            self.display.blit(mode_rect, (5, 5))
            self.__display_tool_tips()

            pygame.display.flip()


if __name__ == "__main__":
    app = App()
    app.run()