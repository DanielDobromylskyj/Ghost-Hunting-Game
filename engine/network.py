import os
import random
import socket
import threading
import io
import time
import tempfile

from .file_api import encode_dict, decode_dict


def send_value(conn, value, compressed=False):
    """ Sends a value of any available datatype """
    buffer = io.BytesIO()
    encode_dict({"data": value}, buffer, should_compress=compressed)
    data = buffer.getvalue()
    buffer.close()
    conn.send(len(data).to_bytes(8))
    conn.send(data)


def recv_value(conn, compressed=False):
    """ Receives a value of any available datatype """
    length = int.from_bytes(conn.recv(8))
    data_encoded = conn.recv(length)

    buffer = io.BytesIO(data_encoded)
    decoded = decode_dict(buffer, is_compressed=compressed)
    buffer.close()

    if "data" not in decoded:
        return None

    return decoded["data"]


class Player:
    username: str = "Unknown"
    last_update: float = 0.0
    position: tuple = (0, 0)
    is_ghost: bool = False
    is_client: bool = False
    ready: bool = False

    def get_info(self):
        return {"username": self.username, "position": self.position, "is_ghost": self.is_ghost,
                "is_client": self.is_client, "ready": self.ready}

    def recv_info(self, info):
        self.username = info["username"]
        self.position = info["position"]
        self.is_ghost = info["is_ghost"]
        self.ready = info["ready"]
        self.last_update = time.time()


class Server:
    MAX_PLAYERS = 5
    SERVER_FPS = 30

    def __init__(self, map_path, port=5678):
        local_ip = socket.gethostbyname(socket.gethostname())

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((local_ip, port))

        self.map_path = map_path
        self.map_data = b""

        self.players = []
        self.mode = "starting"

    def __startup(self):
        """ Starts up the server, run in a thread (from the 'run' method)"""
        with open(self.map_path, "rb") as f:
            self.map_data = f.read()

        self.mode = "lobby"

    def __get_players_information(self):
        return [
            player.get_info()
            for player in self.players
        ]

    def __handle_client(self, conn: socket.socket):
        """ Handles client connections """
        if self.mode == "starting":
            send_value(conn, "server_still_starting")
            time.sleep(1)
            return conn.close()

        elif self.mode != "lobby":
            send_value(conn, "server_in_game")
            time.sleep(1)
            return conn.close()

        send_value(conn, "connected")
        player_info = recv_value(conn)

        player = Player()
        player.recv_info(player_info)

        self.players.append(player)
        player_index = len(self.players) - 1

        while conn:
            request = recv_value(conn)

            if request == "disconnect":
                self.players.remove(conn)
                conn.close()
                break

            elif request == "ping":
                send_value(conn, "pong")

            elif request == "map_data":
                send_value(conn, self.map_data, compressed=True)

            elif request == "tps":
                send_value(conn, self.SERVER_FPS)

            elif request == "player_info":
                send_value(conn, "ready")
                player_info = recv_value(conn)
                self.players[player_index].recv_info(player_info)

            elif request == "other_players_info": # At some stage make this only send close players / visible maybe
               send_value(conn, self.__get_players_information())

        return None

    def run(self):
        """ Starts up the server, then runs a loop to allow connections"""
        threading.Thread(target=self.__startup, daemon=True).start()

        self.sock.listen(5)

        while True:
            conn, addr = self.sock.accept()

            if len(self.players) < Server.MAX_PLAYERS:
                threading.Thread(target=self.__handle_client, args=(conn,), daemon=True).start()

            else:
                send_value(self.sock, "lobby_is_full")
                conn.close()


class Client:
    def __init__(self, render_engine, player: Player, host: str, port: int = 5678):
        self.address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.engine = render_engine
        self.player = player
        self.players = {}
        self.current_ping = 0
        self.error = None

    def hook_render_engine(self):
        self.engine.client = self

    def connect(self) -> str | bool:
        """ Attempts to connect to the server, returns true / error message, if successful / failed"""
        self.sock.connect(self.address)
        response = recv_value(self.sock)

        if response != "connected":
            return response

        send_value(self.sock, self.player.get_info())

        return True

    def disconnect(self) -> None:
        """ Safely disconnects from server """
        send_value(self.sock, "disconnect")
        self.sock.close()

    def ping(self) -> int | None:
        """ Returns time in ms or none if a invalid value is received"""
        start = time.time()
        send_value(self.sock, "ping")
        pong = recv_value(self.sock)
        end = time.time()

        if pong == "pong":
            return round((end - start) / 1000)
        return None

    def get_map_data(self) -> bytes:
        """ Gets the raw file data of the servers loaded map"""
        send_value(self.sock, "map_data")
        return recv_value(self.sock, compressed=True)

    def get_server_tps(self):
        """ Gets the servers desired TPS"""
        send_value(self.sock, "tps")
        return recv_value(self.sock)

    def send_player_info(self):
        """ Update the servers version of out data"""
        send_value(self.sock, "player_info")
        if recv_value(self.sock) != "ready": return
        send_value(self.sock, self.player.get_info())

    def get_other_players_info(self):
        """ Retrieves and updates all player data (including our own)"""
        send_value(self.sock, "other_players_info")
        data = recv_value(self.sock)

        for player_info in data:
            if player_info["username"] not in self.players:
                self.players[player_info["username"]] = Player()

            self.players[player_info["username"]].recv_info(player_info)

    def get_ping(self):
        """ Sets the current ping"""
        self.current_ping = self.ping()

    def load_map(self):
        """ Loads the map data from the servers loaded map and loads it into render engine """
        map_data = self.get_map_data()
        path = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=5)) + "_temp_map.bin"

        try:
            with open(path, "wb") as f:
                f.write(map_data)

            self.engine.load_map(path)
        except:
            os.remove(path)
            raise

        os.remove(path)

    def set_ready(self, ready_status: bool = True) -> None:
        """ Sets player status to "ready" allowing server to start playing """
        self.player.ready = ready_status


    def __start(self) -> None:
        try:
            result = self.connect()

            if result is not True:
                raise ConnectionRefusedError(result)
        except Exception as e:
            self.error = str(e)
            raise

        self.load_map()
        target_tps = self.get_server_tps()
        target_time = 1 / target_tps
        tick_counter = 0

        while True:
            start = time.time()

            # Networking Update Loop

            self.send_player_info()
            self.get_other_players_info()

            if tick_counter % target_tps:
                self.get_ping()


            # End Of Networking Loop

            elapsed = time.time() - start
            if elapsed < target_time:
                time.sleep(target_time - elapsed)

            tick_counter += 1


    def start(self) -> None:
        """ Handles all connections and data transfer, in the background"""
        self.hook_render_engine()
        threading.Thread(target=self.__start, daemon=True).start()
