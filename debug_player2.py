from engine import game
import random, threading, socket

def move_around(player: game.Game):
    dx, dy = 1, 1
    while True:
        dx += (random.random() - 0.5)
        dy += (random.random() - 0.5)

        player.render.position[0] += dx
        player.render.position[1] += dy


host = socket.gethostbyname(socket.gethostname())

p2 = game.Game("Player 2", host, dont_display=True)
p2.client.set_ready(True)

threading.Thread(target=move_around, args=(p2,)).start()

while True:
    p2.render.update_network()
