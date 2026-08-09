import json
import math

import pygame
import numpy as np
from PIL import Image
from io import BytesIO

import maker_v2
from map_maker.maker_v2 import Room


def save_project(path, room_layout: list[maker_v2.Room], object_layout: list, lights: list, switches: list):
    if not path:
        return

    with open(path, "w") as f:
        json.dump({
            "rooms": [
                {
                    "id": room.room_id,
                    "position": [room.world_x, room.world_y],
                    "shape": [room.width, room.height],
                    "colour": room.colour,
                    "floor_tile": room.floor_tile[1] if room.floor_tile else None,
                    "is_hiding_spot": room.hiding_spot,
                    "walls": [
                        {
                            "is_vertical": wall.is_vertical,
                            "doorways": [
                                {
                                    "offset": door.offset,
                                    "width": door.width,
                                    "has_door": door.has_door,
                                }
                                for door in wall.doors
                            ]
                        } if wall is not None else None
                        for wall in room.walls
                    ]
                }
                for room in room_layout
            ],
            "objects": [
                {
                    "position": obj[1],
                    "path": obj[2]
                }
                for obj in object_layout
            ],
            "lights": lights,
            "switches": switches
        }, f)


def load_project(path):
    with open(path, "r") as f:
        data = json.load(f)

    room_layout = []
    for room in data["rooms"]:
        room_instance = maker_v2.Room(room["id"],
                                      room["position"][0], room["position"][1],
                                      room["shape"][0], room["shape"][1],
                                      room["colour"])

        room_instance.hiding_spot = room["is_hiding_spot"]
        room_instance.floor_tile = ( pygame.image.load(room["floor_tile"]).convert_alpha(), room["floor_tile"] )

        room_instance.walls = []
        for wall in room["walls"]:
            wall_instance = maker_v2.Wall(wall["is_vertical"])

            for door in wall["doorways"]:
                door_instance = maker_v2.Door()
                door_instance.offset = door["offset"]
                door_instance.width = door["width"]
                door_instance.has_door = door["has_door"]

                wall_instance.doors.append(door_instance)
            room_instance.walls.append(wall_instance)
        room_layout.append(room_instance)

    object_layout = [
        [pygame.image.load(obj["path"]), obj["position"], obj["path"]]
        for obj in data["objects"]
    ]

    return room_layout, object_layout, data["lights"], data["switches"]


# =============================================== #
# ==>                EXPORTING                <== #
# =============================================== #


def get_bounds(room_layout: list[maker_v2.Room], object_layout: list):
    min_x, max_x, min_y, max_y = [math.inf, -math.inf, math.inf, -math.inf]  # min_x, max_x, min_y, max_y

    for room in room_layout:
        points = (
            (room.world_x, room.world_y),
            (room.world_x + room.width, room.world_y + room.height)
        )

        for x, y in points:
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y

    for img, pos, _ in object_layout:
        points = (
            (pos[0], pos[1]),
            (pos[0] + img.get_width(), pos[1] + img.get_height())
        )

        for x, y in points:
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y

    return [math.floor(min_x), math.floor(min_y)], [math.ceil(max_x), math.ceil(max_y)]

def extract_height_from_path(path: str):  # Some light string manipulation - This system sucks (made it 2 years ago)
    if "NORENDER" in path:
        return 0.0

    return float(".".join(path.split("/")[-1].split("_")[-1].split(".")[:-1]))

def apply_object_heights(height_map, offset, object_layout):
    dx, dy = offset
    for img, pos, path in object_layout:
        x, y = pos
        width, height = img.get_size()
        value = extract_height_from_path(path)

        print(value)

        # fy1:fy2, fx1:fx2
        height_map[y+dy:y+dy + height, x+dx:x+dx + width] = value

def apply_wall_heights(height_map, offset, room_layout: list[maker_v2.Room], wall_thickness=3):
    def fill(fx1, fy1, fx2, fy2, value):
        height_map[fy1:fy2, fx1:fx2] = value

    dx, dy = offset
    for room in room_layout:
        x1, y1 = room.world_x + dx, room.world_y + dy
        x2, y2 = x1 + room.width, y1 + room.height

        wall_points = (
            (x1, y1, x2, y1, 1), (x2, y1, x2, y2, 1),
            (x1, y2, x2, y2, -1), (x1, y1, x1, y2, -1)
        )

        for i, wall in enumerate(room.walls):
            if wall is None:
                continue

            sx, sy, ex, ey, normal = wall_points[i]

            wall.doors.sort(key=lambda door: door.offset)  # quick check, not perfect, but quick

            current = [sx, sy]
            for door in wall.doors:
                if wall.is_vertical:
                    start = round(sy + door.offset)
                    end = round(sy + door.offset + door.width)

                    if start < current[1]:
                        raise ValueError("At least 2 doors are interesting on a single wall")

                    fill(current[0], current[1], sx + (normal * wall_thickness), start, 1)
                    current = [sx, end]

                else:
                    start = round(sx + door.offset)
                    end = round(sx + door.offset + door.width)

                    if start < current[0]:
                        raise ValueError("At least 2 doors are interesting on a single wall")

                    fill(current[0], current[1], start, sy + (normal * wall_thickness), 1)
                    current = [end, sy]

            if wall.is_vertical:
                fill(current[0], current[1], ex + (normal * wall_thickness), ey, 1)

            else:
                fill(current[0], current[1], ex, ey + (normal * wall_thickness), 1)

def apply_lighting(light_map, id_map, lights: list, offset):
    lh, lw = int(light_map.shape[0]), int(light_map.shape[1])
    # [(x, y), brightness {0f-1f}, radius {int}, on_by_default {bool}, room_id]
    for id, ((x, y), brightness, radius, _, _) in enumerate(lights):
        x += offset[0]
        y += offset[1]

        for mx in range(round(max(0, x-radius)), round(min(lw, x+radius))):
            for my in range(round(max(0, y-radius)), round(min(lh, y+radius))):
                distance_squared = ((x-mx)**2 + (y-my)**2)

                if distance_squared > radius * radius:
                    continue

                distance = math.sqrt(distance_squared)
                t = min(distance / radius, 1.0)

                intensity = brightness * ((1 - t) ** 2)

                scaled = min(max(0, intensity), 0.8) * 1.25

                light_map[my, mx] = min(255, light_map[my, mx] + scaled * 255)
                id_map[my, mx] |= 1 << id


def export(path, room_layout: list[maker_v2.Room], object_layout: list, lights: list, switches: list):
    SAVE_VERSION = 2
    bounds = get_bounds(room_layout, object_layout)

    padding = 5
    map_size = (bounds[1][0] - bounds[0][0] + (padding*2), bounds[1][1] - bounds[0][1] + (padding*2))
    offset = (-bounds[0][0] + padding, -bounds[0][1] + padding)
    # > Create Height Map
    inverted_map_size = (map_size[1], map_size[0])
    height_map = np.zeros(inverted_map_size, dtype=np.float32)

    apply_object_heights(height_map, offset, object_layout)
    apply_wall_heights(height_map, offset, room_layout)

    # > Create Light Maps
    light_level_map = np.full(inverted_map_size, 0, dtype=np.float32)
    light_id_map = np.full(inverted_map_size, 0, dtype=np.uint64)

    apply_lighting(light_level_map, light_id_map, lights, offset)

    def write_image(file, img_fp: str | Image.Image):
        if isinstance(img_fp, str):
            with Image.open(img_fp) as img_file:
                buffer = BytesIO()
                img_file.save(buffer, format="png")
                image_bytes = buffer.getvalue()

        else:
            buffer = BytesIO()
            img_fp.save(buffer, format="png")
            image_bytes = buffer.getvalue()

        file.write(len(image_bytes).to_bytes(8, byteorder="big"))
        file.write(image_bytes)


    # Generate Background image
    background_image = Image.new("RGB", map_size, (0, 0, 0))

    for room in room_layout:
        x, y = room.world_x, room.world_y
        w, h = round(room.width), round(room.height)

        if room.floor_tile:
            sub_image = Image.new("RGB", (w, h))

            tile_path = room.floor_tile[1]
            tile = Image.open(tile_path)
            tw, th = tile.width, tile.height

            for dx in range(0, w, tw):
                for dy in range(0, h, th):
                    sub_image.paste(tile, (dx, dy))

            background_image.paste(sub_image, (round(x + offset[0]), round(y + offset[1])))

    # Write data
    with open(path, "wb") as f:
        f.write(SAVE_VERSION.to_bytes(2, byteorder="big"))

        write_image(f, background_image)

        f.write(len(object_layout).to_bytes(4, byteorder="big"))

        pre_sent = {}
        for i, obj in enumerate(object_layout):
            _, pos, path = obj

            pos: tuple[int, int]

            f.write((pos[0] + padding).to_bytes(4, byteorder="big", signed=True))
            f.write((pos[1] + padding).to_bytes(4, byteorder="big", signed=True))
            f.write(round(extract_height_from_path(path) * 255).to_bytes(1, byteorder="big"))

            if path in pre_sent:
                f.write(b"C")  # Cached
                f.write(pre_sent[path].to_bytes(4, byteorder="big"))

            else:
                f.write(b"N")  # New
                write_image(f, path)
                pre_sent[path] = i

        f.write(len(switches).to_bytes(4, byteorder="big"))

        for switch in switches:
            x, y, rx, ry, room_id = switch

            room_lights = [ # [(x, y), brightness {0f-1f}, radius {int}, on_by_default {bool}, room_id]
                i for i, light in enumerate(lights)
                if light[-1] == room_id
            ]

            f.write(round(x).to_bytes(8, byteorder="big"))
            f.write(round(y).to_bytes(8, byteorder="big"))
            f.write(rx.to_bytes(1, byteorder="big", signed=True))
            f.write(ry.to_bytes(1, byteorder="big", signed=True))

            f.write(len(room_lights).to_bytes(1, byteorder="big"))

            for light_id in room_lights:
                f.write(light_id.to_bytes(1, byteorder="big"))
                f.write(b"O" if lights[light_id][3] else b"F") # Default On/oFf

        f.write(len(lights).to_bytes(4, byteorder="big"))

        for (x, y), brightness, radius, on_by_default, room_id in lights:
            f.write(round(x).to_bytes(8, byteorder="big"))
            f.write(round(y).to_bytes(8, byteorder="big"))
            f.write(round(radius).to_bytes(4, byteorder="big"))

        height_data = height_map.tobytes()
        height_map_width, height_map_height = height_map.shape

        f.write(height_map_width.to_bytes(2, byteorder="big"))
        f.write(height_map_height.to_bytes(2, byteorder="big"))
        f.write(len(height_data).to_bytes(4, byteorder="big"))
        f.write(height_data)

        light_data = light_level_map.tobytes()
        light_map_width, light_map_height = light_level_map.shape

        f.write(light_map_width.to_bytes(2, byteorder="big"))
        f.write(light_map_height.to_bytes(2, byteorder="big"))
        f.write(len(light_data).to_bytes(4, byteorder="big"))
        f.write(light_data)

        light_data = light_id_map.tobytes()
        light_map_width, light_map_height = light_id_map.shape

        f.write(light_map_width.to_bytes(2, byteorder="big"))
        f.write(light_map_height.to_bytes(2, byteorder="big"))
        f.write(len(light_data).to_bytes(4, byteorder="big"))
        f.write(light_data)



