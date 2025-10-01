from PIL import Image
import numpy as np
import pygame

from .logger import Log

class DefaultAsset:
    raw = None
    def __init__(self, path):
        self.path = path

        self.reload()

    def reload(self):
        """ Reloads contents stored on the cpu and gpu """
        self.raw = None
        self.raw = self.load_raw(self.path)

    def load_raw(self, path: str):
        """
        Loads data from a given path, all assets need to implement this method

        :param path: string
        :return: Numpy array containing data to send to the gpu
        """
        raise NotImplementedError()


class Texture2D(DefaultAsset):
    image_mode = "RGBA"

    texture_width: int
    texture_height: int
    image_width: int
    image_height: int
    channels: int

    pygame_surface = None

    def __init__(self, path: str, quality: float, load_pygame: bool, mode: str):
        """
        Loads a texture from the given path given a quality from 0 to 1 where 1 is standard resolution/scale

        :param path: str
        :param quality: float
        """

        self.image_mode = mode
        self.quality = quality
        self.use_pygame = load_pygame
        super().__init__(path)


    def load_raw(self, path):
        texture = pygame.image.load(path).convert_alpha()
        self.image_width = texture.get_width()
        self.image_height = texture.get_height()
        self.channels = len(self.image_mode)


        if self.use_pygame:
            if not pygame.get_init():
                pygame.init()

            self.pygame_surface = texture

        Log.log(f"Loaded Texture2D: {path}")

        # get raw data
        return texture.get_buffer().raw
