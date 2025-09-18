import math

import numpy as np
import pygame
from matplotlib import pyplot as plt


class MapLoadingException(Exception):
    pass


class Map:
    MAP_VERSION = 1

    background_img = None
    scene = {}
    __maps = {}

    def __init__(self, render_engine):
        self.render_engine = render_engine

        self.__path_replacements = {
            "%DATA%": "data",
            "%TEXTURES%": "data/textures",
        }

    def __to_path(self, path):
        """ Replaces any %LOCATION% with the actual path"""
        for k, v in self.__path_replacements.items():
            path = path.replace(k, v)
        return path

    def load_layout(self, layout: dict) -> None:
        if layout["version"] > self.MAP_VERSION:
            raise MapLoadingException("Invalid map version!")

        texture_index = self.render_engine.load_texture(
            self.__to_path(layout["background"])
        )

        self.__maps["height"] = layout["map"]["height"]
        self.__maps["light"] = layout["map"]["light"]

        self.background_img = self.render_engine.get_asset(texture_index).pygame_surface

        self.scene = {}
        for world_object in layout["objects"]:
            if world_object["name"] in self.scene:
                raise MapLoadingException("Found two objects with the same name!")


            self.scene[world_object["name"]] = {
                "position": world_object["position"],
                "height": world_object["height"],
                "texture_id": self.render_engine.load_texture(
                    self.__to_path(world_object["path"])
                ),
                "path": self.__to_path(world_object["path"]),
            }

    def get_pygame_texture(self, world_object):
        return self.render_engine.get_asset(
            world_object["texture_id"]
        ).pygame_surface

    def get_object_shape(self, world_object):
        return self.get_pygame_texture(world_object).get_size()

    def get_size(self):
        max_x, max_y = self.background_img.get_size()

        for name, world_object in self.scene.items():
            pos = world_object["position"]

            w, h = self.get_object_shape(world_object)

            if max_x < w + pos[0]:
                max_x = w + pos[0]

            if max_y < h + pos[1]:
                max_y = h + pos[1]

        return max_y, max_x


    def compute_light_map(self):
        return self.__maps["light"]  # Computed and stored in the save file now

    def compute_height_map(self):
        return self.__maps["height"]  # Computed and stored in the save file now


class LoadedMap(Map):
    MAP_VERSION = 1

    def __init__(self, render_engine, path):
        super().__init__(render_engine)
        self.load(path)

    def load(self, path):
        def read_string(file, length=2):
            length = int.from_bytes(file.read(length))

            if length == 0:
                return None

            content = file.read(length)
            return content.decode()

        def load_map(file):
            width, height = int.from_bytes(file.read(2)), int.from_bytes(file.read(2))
            data_length = int.from_bytes(file.read(4))
            data = file.read(data_length)

            return np.frombuffer(data, dtype=np.float32).reshape(width, height)

        layout = {}
        with open(path, "rb") as f:
            layout["version"] = int.from_bytes(f.read(1))

            if layout["version"] != self.MAP_VERSION:
                raise MapLoadingException("Invalid map version!")

            layout["background"] = read_string(f)
            object_count = int.from_bytes(f.read(4))

            layout["objects"] = [
                {
                    "name": read_string(f),
                    "position": (int.from_bytes(f.read(2)), int.from_bytes(f.read(2))),
                    "height": int.from_bytes(f.read(2)) / 1000,
                    "path": read_string(f),
                } for _ in range(object_count)
            ]

            layout["map"] = {
                "height": load_map(f),
                "light": load_map(f)
            }

        self.load_layout(layout)







class DemoMap(Map):
    def __init__(self, render_engine):
        super().__init__(render_engine)

        self.load_layout({
            "version": 1,
            "background": "%TEXTURES%/demo_background.png",
            "objects": [
                {
                    "name": "demo-table",  # this will likely just be a UUID
                    "path": "%TEXTURES%/demo_object.png",
                    "position": (100, 500),
                    "height": 0.6  # Where 1 is max height (Like a wall)
                },
                {
                    "name": "demo-table-short",  # this will likely just be a UUID
                    "path": "%TEXTURES%/demo_object.png",
                    "position": (100, 300),
                    "height": 0.3  # Where 1 is max height (Like a wall)
                }
            ]
        })
