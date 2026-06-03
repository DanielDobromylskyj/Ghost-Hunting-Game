import json
import pygame

import maker_v2


def save_project(path, room_layout: list[maker_v2.Room], object_layout: list):
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
            ]
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

    return room_layout, object_layout


def export(path, room_layout, object_layout):
    pass  # todo
