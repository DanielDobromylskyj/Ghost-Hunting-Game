import random

from engine import game
from engine.hns import run_server as run_server_with_ngrok
import socket

"""
How to host on uni wifi

Ensure "ngrok" is installed / logged in 
Then import network stuff from the nhs sub section of the engine module

"""


debug = input("Debug Mode? (Y/n)").lower() != "n"

if debug:
    host = socket.gethostbyname(socket.gethostname())
    username = "Test User"
    is_hosting = True

else:
    print("Local:", socket.gethostbyname(socket.gethostname()))
    host = input("Enter the host ip address: ")
    username = input("Enter Username: ")
    is_hosting = input("Are you hosting (y/N)").lower() == "y"


if is_hosting:
    from engine.network import Server
    import threading, time

    server = Server("data/demo_map.bin")

    print("Letting server start...")
    threading.Thread(target=server.run, daemon=True).start()
    time.sleep(5)

instance = game.Game(username, host)
instance.start()

