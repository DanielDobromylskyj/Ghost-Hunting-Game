import pygame

from .render import Render as RenderEngine

class Game:
    def __init__(self):
        self.render = RenderEngine()
        self.render.load_map()

        self.clock = pygame.time.Clock()


    def start(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            keys = pygame.key.get_pressed()

            if keys[pygame.K_w]:
                self.render.position[0] -= 1

            if keys[pygame.K_s]:
                self.render.position[0] += 1

            if keys[pygame.K_a]:
                self.render.position[1] -= 1

            if keys[pygame.K_d]:
                self.render.position[1] += 1


            self.render.render_scene()
            self.render.display_fps(self.clock.get_fps())
            pygame.display.flip()

            self.clock.tick()
