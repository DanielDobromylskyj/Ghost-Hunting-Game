import numpy as np
import uuid
import os


class MapLoadingException(Exception):
    pass


class Map:
    MAP_VERSION = 1

    background_img = None
    scene = {}
    __maps = {}
    __lights = []

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
        if layout["version"] not in (1, 2):
            raise MapLoadingException("Invalid map version!")

        texture_index = self.render_engine.load_texture(
            self.__to_path(layout["background"])
        )

        self.__maps["height"] = layout["map"]["height"]
        self.__maps["light"] = layout["map"]["light"]

        self.__lights = layout["lights"]

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

    def get_lights(self):
        return self.__lights

def read_string(file, length=2):
    length = int.from_bytes(file.read(length), byteorder="big")

    if length == 0:
        return None

    content = file.read(length)
    return content.decode()

def load_map(file, expected_dtype=None):
    if expected_dtype is None:
        expected_dtype = np.float32

    width, height = int.from_bytes(file.read(2), byteorder="big"), int.from_bytes(file.read(2), byteorder="big")
    data_length = int.from_bytes(file.read(4), byteorder="big")
    data = file.read(data_length)
    return np.frombuffer(data, dtype=expected_dtype).reshape(width, height)

def read_path(file, length=2):
    data = read_string(file, length)
    if "../" in data: raise FileNotFoundError("Bad Path!")  # Stop
    return data

class LoadedMap(Map):
    MAP_VERSION_1 = 1
    MAP_VERSION_2 = 2

    def __init__(self, render_engine, path):
        super().__init__(render_engine)
        self.temp_path = "data/temp/map/"
        self.temp_load_cache = {}
        self.images_loaded = 0

        self.load(path)

    def wipe_temp(self):
        for sub_path in os.listdir(self.temp_path):
            true_path = os.path.join(self.temp_path, sub_path)

            if os.path.isfile(true_path):
                os.remove(true_path)

    def temp_load_image(self, file) -> str:
        """ Loads an image from the binary file and stores it in the temp directory, returns its path."""
        image_uuid = str(uuid.uuid4())
        path = os.path.join(self.temp_path, f"{image_uuid}.png")

        byte_count = int.from_bytes(file.read(8), byteorder="big")
        image_bytes = file.read(byte_count)

        with open(path, "wb") as image_file:
            image_file.write(image_bytes)

        return path

    def temp_load_with_cache(self, file) -> str:
        mode = file.read(1)


        if mode == b"N":  # New
            path = self.temp_load_image(file)
            self.temp_load_cache[self.images_loaded] = path

        elif mode == b"C": # Cached
            index = int.from_bytes(file.read(4), byteorder="big")
            path = self.temp_load_cache[index]

        else:
            raise MapLoadingException(f"Unknown mode when loading object: {mode}")

        self.images_loaded += 1
        return path

    def load_v2(self, path):
        self.wipe_temp()

        layout = {}
        with open(path, "rb") as f:
            layout["version"] = int.from_bytes(f.read(2), byteorder="big")

            if layout["version"] != self.MAP_VERSION_2:
                raise MapLoadingException("Invalid map version!")

            layout["background"] = self.temp_load_image(f)

            object_count = int.from_bytes(f.read(4), byteorder="big")

            layout["objects"] = [
                {
                    "position": (int.from_bytes(f.read(4), byteorder="big", signed=True),
                                 int.from_bytes(f.read(4), byteorder="big", signed=True)),
                    "height": int.from_bytes(f.read(1), byteorder="big") / 255,
                    "path": self.temp_load_with_cache(f),
                    "name": str(uuid.uuid4())
                } for _ in range(object_count)
            ]

            layout["switches"] = [
                {
                    "position": (int.from_bytes(f.read(8), byteorder="big"),
                                 int.from_bytes(f.read(8), byteorder="big")),

                    "facing": (int.from_bytes(f.read(1), byteorder="big", signed=True),
                                 int.from_bytes(f.read(1), byteorder="big", signed=True)),

                    "lights": [
                        {
                            "id": int.from_bytes(f.read(1), byteorder="big"),
                            "enabled": f.read(1) == b"O"
                        } for _ in range(int.from_bytes(f.read(1), byteorder="big"))
                    ]
                } for _ in range(int.from_bytes(f.read(4), byteorder="big"))
            ]

            layout["lights"] = [
                {
                    "position": (int.from_bytes(f.read(8), byteorder="big"),
                                 int.from_bytes(f.read(8), byteorder="big")),
                    "radius": int.from_bytes(f.read(4), byteorder="big")
                }
                for _ in range(int.from_bytes(f.read(4), byteorder="big"))
            ]


            layout["map"] = {
                "height": load_map(f, expected_dtype=np.float32),
                "light": load_map(f, expected_dtype=np.float32),
                "light-ids": load_map(f, expected_dtype=np.uint64),
            }

        self.load_layout(layout)

    def load(self, path):
        layout = {}
        with open(path, "rb") as f:
            layout["version"] = int.from_bytes(f.read(2), byteorder="big")

            if layout["version"] == self.MAP_VERSION_2:
                f.close()

                self.load_v2(path)
                return

            elif layout["version"] != self.MAP_VERSION_1:
                raise MapLoadingException(f"Invalid map version! ({layout['version']})")

            layout["background"] = read_string(f)
            object_count = int.from_bytes(f.read(4), byteorder="big")

            layout["objects"] = [
                {
                    "name": read_string(f),
                    "position": (int.from_bytes(f.read(2), byteorder="big"), int.from_bytes(f.read(2), byteorder="big")),
                    "height": int.from_bytes(f.read(2), byteorder="big") / 1000,
                    "path": read_path(f),
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
