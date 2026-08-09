from engine import game
import socket


debug = input("Debug Mode? (Y/n)").lower() != "n"

server_ip = "127.0.0.1"

if debug:
    host = socket.gethostbyname(socket.gethostname())
    server_ip = "127.0.0.1"
    username = "Test User"

else:
    print("Local:", socket.gethostbyname(socket.gethostname()))
    host = input("Enter the host ip address: ")
    username = input("Enter Username: ")


instance = game.Game(username, host)


try:
    instance.render.DEBUG = True
    instance.start()
except:
    raise

