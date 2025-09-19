import pygame

from .render import Render as RenderEngine
from .network import Client, Player

class Game:
    def __init__(self, username, host):
        self.render = RenderEngine()

        self.player = Player()
        self.player.username = username

        self.client = Client(self.render, self.player, host)
        self.client.start()

        self.clock = pygame.time.Clock()
        self.walk_speed = 100


    def start(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_g:
                        if not self.client.player.ready:
                            self.client.set_ready(True)

            delta = self.clock.get_time() / 1000
            keys = pygame.key.get_pressed()

            if keys[pygame.K_w]:
                self.render.position[0] -= self.walk_speed * delta

            if keys[pygame.K_s]:
                self.render.position[0] += self.walk_speed * delta

            if keys[pygame.K_a]:
                self.render.position[1] -= self.walk_speed * delta

            if keys[pygame.K_d]:
                self.render.position[1] += self.walk_speed * delta


            self.render.render_scene()
            self.render.display_fps(self.clock.get_fps())
            pygame.display.flip()

            self.clock.tick()
