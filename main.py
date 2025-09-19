from engine import game
import socket

"""
How to host on uni wifi (Not working)

Open cmd -> run "ssh -R 80:localhost:5678 serveo.net"
Copy the Hostname from the terminal (Do not include final slash or starting https://)
Use that hostname for external clients

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
    threading.Thread(target=server.run, daemon=True).start()

    print("Letting server start...")
    time.sleep(2)

    if debug:
        p2 = game.Game("Player 2", host)
        p2.client.set_ready(True)

instance = game.Game(username, host)
instance.start()

