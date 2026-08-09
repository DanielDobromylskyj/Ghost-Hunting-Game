from engine.network import Server
import socket

def main():
    ip = "127.0.0.1" # socket.gethostbyname(socket.gethostname())
    print("Starting server on:", ip)

    server = Server("test.bin", ip)

    try:
        server.run()
    except KeyboardInterrupt:
        print("Server shutting down...")

if __name__ == "__main__":
    main()