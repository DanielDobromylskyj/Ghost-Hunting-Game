import pygame


class Item:
    def __init__(self, name):
        self.name = name
        self.__model = None

    def get_model(self):
        if self.__model is None:
            self.__model = pygame.image.load("data/textures/item/"+self.name+".png")

        return self.__model
