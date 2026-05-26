from engine import game
import socket


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
    time.sleep(3)

instance = game.Game(username, host)
instance.render.DEBUG = True
instance.start()

