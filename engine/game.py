import pygame

from .render import Render as RenderEngine
from .network import Client, Player
from .logger import Log
from .item import Item
from .tablet_system import TabletSystem


class Game:
    def __init__(self, username, host, port=5678, dont_display=False):
        if not dont_display:
            Log().new()
            Log.log('Welcome To \'Untitled Ghost Hunting Game\'')

        self.inventory = [Item("torch"), None, None]
        self.inventory_index = 0

        self.player = Player()
        self.player.username = username

        self.render = RenderEngine(self, dont_display=dont_display)
        self.tablet = TabletSystem(self.render.display_size)

        self.client = Client(self.render, self.player, host, port)
        self.client.start()

        self.clock = pygame.time.Clock()
        self.walk_speed = 100

    def update_network(self, update_ping: bool):
        self.client.update_network()

        if update_ping:
            self.client.update_ping()

    def on_exit(self):
        self.client.proxy_chat.stop()
        self.client.disconnect()

    def start(self):
        Log.log("Game starting")
        counter = 0

        looking_pos = (-1, -1)
        while True:
            # Network Tick
            self.update_network(counter % 60 == 0)

            if not self.render.dont_display:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.on_exit()
                        pygame.quit()
                        exit()

                    if event.type == pygame.MOUSEMOTION:
                        looking_pos = event.pos

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_g:
                            if not self.client.player.ready:
                                self.client.set_ready(True)

                        if event.key == pygame.K_j:
                            self.tablet.toggle_open()

                        # DEBUG START
                        if event.key == pygame.K_F1:
                            self.render.debug_toggle()

                        if event.key == pygame.K_1:
                            self.render.toggle_light(0)

                        if event.key == pygame.K_2:
                            self.render.toggle_light(0, update=False)
                            self.render.toggle_light(1)

                        if event.key == pygame.K_3:
                            self.render.toggle_light(2)
                        # DEBUG END

                        if event.key == pygame.K_b:
                            self.client.set_radio(True)

                    if event.type == pygame.KEYUP:
                        if event.key == pygame.K_b:
                            self.client.set_radio(False)

                delta = self.clock.get_time() / 1000
                keys = pygame.key.get_pressed()

                self.render.update_player_orientation(*looking_pos)

                moved = False
                if keys[pygame.K_w]:
                    self.render.position[0] -= self.walk_speed * delta
                    moved = True

                if keys[pygame.K_s]:
                    self.render.position[0] += self.walk_speed * delta
                    moved = True

                if keys[pygame.K_a]:
                    self.render.position[1] -= self.walk_speed * delta
                    moved = True

                if keys[pygame.K_d]:
                    self.render.position[1] += self.walk_speed * delta
                    moved = True


                self.render.set_player_moving(moved)
                self.render.render_scene(delta)
                self.render.display_fps(self.clock.get_fps())
                pygame.display.flip()

            else:
                self.render.update_player_orientation((counter * 1) % 1920, 0)

            self.clock.tick()
            counter += 1