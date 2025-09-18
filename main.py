from engine import game

"""
How to host on uni wifi

Open cmd -> run "ssh -R 80:localhost:5678 serveo.net"
Copy the Hostname from the terminal (Do not include final slash or starting https://)
Use that hostname for external clients

"""


debug = input("Debug Mode? (Y/n)").lower() != "n"

instance = game.Game()
instance.start()

