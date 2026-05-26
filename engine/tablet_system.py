import pygame

from . import ghost
from .logger import Log

Ghost_Types = [
    (attr_name, value(load=False))
    for attr_name, value in vars(ghost).items()
    if "__" not in attr_name
    if isinstance(value, type) and issubclass(value, ghost.GenericGhost)
    if attr_name != "GenericGhost"
]

class TabletSystem:
    TABLET_IS_ON_LEFT = True
    def __init__(self, display_size):
        self.display_size = display_size

        self.tablet_open = False
        self.status = "off"
        self.loading_timer = 0
        self.page_open = None

        self.name_font = pygame.font.SysFont("Arial", 20)
        self.ghost_names_per_line = 0

        w, h = self.get_tablet_size()
        self.tablet_display = pygame.Surface((w, h))
        self.ghost_options_surface = self.create_ghost_options(w - 20, h - 300)
        self.ghost_options = {name: 0 for name, _ in Ghost_Types}

        Log.log(f"Found {len(Ghost_Types)} ghost types")
        Log.log(f"Premade tablet display and ghost options")

    def create_ghost_options(self, w, h):
        surface = pygame.Surface((w, h), pygame.SRCALPHA)

        option_width = 150
        option_height = 50

        self.ghost_names_per_line = w // option_width

        x = 0
        y = 0

        for name, _ in Ghost_Types:
            rect = self.name_font.render(name, True, (230, 230, 230))

            surface.blit(rect, (x + (option_width - rect.get_width()) / 2, y))

            x += option_width

            if x + option_width > w:
                x = 0
                y += option_height

        return surface


    def get_tablet_size(self):
        aspect_ratio = 1 / 1.5

        if self.display_size[0] > self.display_size[1]:
            height = self.display_size[1] * 0.9
            width = height * aspect_ratio

        else:
            width = self.display_size[0] * 0.9
            height = width / aspect_ratio

        return width, height


    def turn_on(self):
        self.status = "load"
        self.loading_timer = 0

    def toggle_open(self):
        if self.status == "off" and not self.tablet_open:
            self.turn_on()

        self.tablet_open = not self.tablet_open

    def __render(self, display):
        if self.tablet_open:
            if self.TABLET_IS_ON_LEFT:
                sx = (self.tablet_display.get_width() * 0.1)
            else:
                sx = (display.get_width() - self.tablet_display.get_width()) / 2

            sy = (display.get_height() - self.tablet_display.get_height()) / 2

            display.blit( self.tablet_display, ( sx, sy ) )

            pygame.draw.rect(display, (130, 130, 130), (sx-3, sy-3, self.tablet_display.get_width()+6, self.tablet_display.get_height()+6), border_radius = 5, width=5)

    def click(self, event):
        pass

    def __draw_main_menu(self):
        self.tablet_display.blit(self.ghost_options_surface, (
            (self.tablet_display.get_width() - self.ghost_options_surface.get_width()) / 2,
            300
        ))

    def tick(self, display, delta_time):
        if self.status == "off":
            self.tablet_display.fill((0, 0, 0))

        elif self.status == "load":
            self.loading_timer += delta_time
            self.tablet_display.fill((50, 50, 50))

            if self.loading_timer > 1:
                self.status = "on"
                self.tablet_display.fill((10, 10, 10))

        elif self.status == "on":
            if self.page_open is None:
                self.__draw_main_menu()


        self.__render(display)
