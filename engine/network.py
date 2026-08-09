import math
import os
import random
import socket
import threading
import io
import time
import tempfile
from typing import Any
import pygame

from packet_manager import *
from packet_manager.udp_handshake import PeerServer as Server_UDP_Handshake
from packet_manager.udp_handshake import Client as Client_UDP_Handshake

from .file_api import encode_dict, decode_dict
from .logger import Log
from .audio_engine import ProxyChat


def send_value(conn, value, compressed=False):
    """ Sends a value of any available datatype """
    buffer = io.BytesIO()
    encode_dict({"data": value}, buffer, should_compress=compressed)
    data = buffer.getvalue()
    buffer.close()
    conn.send(len(data).to_bytes(8, byteorder="big"))
    conn.send(data)


def recv_value(conn, compressed=False):
    """ Receives a value of any available datatype """
    length = int.from_bytes(conn.recv(8), byteorder="big")
    data_encoded = conn.recv(length)

    buffer = io.BytesIO(data_encoded)
    decoded = decode_dict(buffer, is_compressed=compressed)
    buffer.close()

    if "data" not in decoded:
        print("Uh Oh:", decoded, data_encoded)
        return None

    return decoded["data"]

def read_value(data: bytes, compressed=False):
    buffer = io.BytesIO(data)
    decoded = decode_dict(buffer, is_compressed=compressed)
    buffer.close()

    if "data" not in decoded:
        print("Uh Oh:", decoded, data)
        return None

    return decoded["data"]

def write_value(value, compressed=False):
    buffer = io.BytesIO()
    encode_dict({"data": value}, buffer, should_compress=compressed)
    data = buffer.getvalue()
    buffer.close()
    return data


class Player:
    username: str = "Unknown"
    last_update: float = 0.0
    position: tuple = (0, 0),
    rotation: float = 0
    is_ghost: bool = False
    is_client: bool = False
    ready: bool = False
    voice_audio: list
    using_radio: bool = False

    def get_info(self):
        return {"username": self.username, "position": self.position, "is_ghost": self.is_ghost,
                "is_client": self.is_client, "ready": self.ready, "rotation": self.rotation}

    def recv_info(self, info):
        self.username = info["username"]
        self.position = info["position"]
        self.is_ghost = info["is_ghost"]
        self.rotation = info["rotation"]
        self.ready = info["ready"]
        self.last_update = time.time()

    def voice_callback(self, input_data):
        self.voice_audio.append(input_data)


class Server:
    MAX_PLAYERS = 5
    SERVER_FPS = 60

    def __init__(self, map_path, public_ip, port=5678, debug_on_lan=False):
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.public_ip = public_ip
        self.port = port

        self.__debug_on_lan = debug_on_lan

        Log.log(f"Starting Server. Public: {self.public_ip}, Local: {self.local_ip}, Port: {self.port}")

        self.sock = createTCPsocket()
        self.sock.bind((self.local_ip, port))

        self.udp_connection = createUDPsocket()
        self.udp_connection.bind((self.local_ip, port+1))

        self.map_path = map_path
        self.map_data = b""

        self.max_voice_distance = 500

        self.players: list[Player] = []
        self.connections = []
        self.__addr_lookup: dict[str, int] = {}

        self.mode = "starting"

    def __startup(self):
        """ Starts up the server, run in a thread (from the 'run' method)"""
        Log.log(f"Loading Map Data...")
        with open(self.map_path, "rb") as f:
            self.map_data = f.read()

        self.mode = "lobby"

        Log.log(f"Entering Update Loop")

        tick = 0
        clock = pygame.time.Clock()

        while True:
            self.__update_networks()
            self.__update_player_positions()

            clock.tick(self.SERVER_FPS)


    def __get_players_information(self):
        return [
            player.get_info()
            for player in self.players
        ]

    @staticmethod
    def unknown_packet_callback(conn_manager, packet_type, data, protocol):
        print(f"WARNING: SERVER Unknown {protocol} Packet Type -> {packet_type}: {data}")

    def on_disconnect(self, conn_manager: ConnectionTCP, data: bytes):
        try:
            self.players.remove(self.__get_player_from_conn(conn_manager))
        except ValueError:
            pass

        conn_manager.sock.close()

    @staticmethod
    def on_ping(conn_manager: ConnectionTCP, data: bytes):
        conn_manager.send("pong", b"")

    def on_map_request(self, conn_manager: ConnectionTCP, data: bytes):
        conn_manager.send("map_data", self.map_data)

    def on_tps(self, conn_manager: ConnectionTCP, data: bytes):
        conn_manager.send("tps", self.SERVER_FPS.to_bytes(8, byteorder="big"))

    def on_player_toggle_radio(self, conn_manager: ConnectionTCP, data: bytes):
        player: Player = self.__get_player_from_conn(conn_manager)

        player.using_radio = data == b"1"

    def on_player_info(self, conn_manager: ConnectionUDP, sender, data: bytes):
        player = self.__get_player_from_addr(sender)
        player.recv_info(read_value(data))

    def on_other_players_info(self, conn_manager: ConnectionUDP, sender, data: bytes):
        conn_manager.send("player_data", write_value(self.__get_players_information()))

    def on_recv_voice_data(self, conn_manager: ConnectionUDP, sender, data: bytes):
        send_player: Player = self.__get_player_from_addr(sender)
        send_pos = send_player.position if type(send_player.position[0]) in (int, float) else send_player.position[0]

        for conn_tcp, conn_udp in self.connections:
            if conn_udp == conn_manager: # Stop player hearing themselves
                continue

            # Calculate Relative Position / Volume
            recv_player: Player = self.__get_player_from_conn(conn_tcp)
            recv_pos = recv_player.position if type(recv_player.position[0]) in (int, float) else recv_player.position[0]

            dx = recv_pos[0] - send_pos[0]
            dy = recv_pos[1] - send_pos[1]

            dist = math.sqrt(dx*dx + dy*dy)
            volume = max(0, (self.max_voice_distance - dist) / self.max_voice_distance)

            if send_player.using_radio:
                volume = 1

            conn_udp.send("ProxyVoiceToClient", write_value({
                "bytes": data, "from": sender,
                "vol": volume, "radio": send_player.using_radio,
                "rel_x": dx, "rel_y": dy
            }))

    def __get_player_from_conn(self, conn: ConnectionUDP | ConnectionTCP) -> Player:
        if hasattr(conn, "_player_index"):
            player = self.players[getattr(conn, "_player_index")]

            if isinstance(player, Player):
                return player

            else:
                raise TypeError("Unknown Player Class!")

        else:
            raise AttributeError("Player Doesn't Have Connection Set!")

    def __get_player_from_addr(self, addr: tuple[str, int]):
        ip, port = addr

        if ip in self.__addr_lookup:
            player_id = self.__addr_lookup[ip]
            return self.players[player_id]

        else:
            raise LookupError


    def __handle_client(self, conn: socket.socket, addr: tuple[str, int]):
        """ Handles client connections """
        if self.mode == "starting":
            send_value(conn, "server_still_starting")
            time.sleep(1)
            return conn.close()

        elif self.mode != "lobby":
            send_value(conn, "server_in_game")
            time.sleep(1)
            return conn.close()

        # Setup TCP
        callbacks_tcp = {
            b"disconnect": self.on_disconnect,
            b"ping": self.on_ping,
            b"map_data": self.on_map_request,
            b"tps": self.on_tps,

            b"set_radio": self.on_player_toggle_radio
        }


        packet_manager_tcp = ConnectionTCP(conn, callbacks_tcp, self.unknown_packet_callback)
        Log.log("Established TCP")

        # Setup UDP
        udp_con = Server_UDP_Handshake.request_udp_connection(packet_manager_tcp, self.udp_connection)

        if not isinstance(udp_con, ConnectionUDP):
            raise TypeError

        udp_con.add_packet_callback("ProxyVoiceToServer", self.on_recv_voice_data)
        udp_con.add_packet_callback("player_info", self.on_player_info)

        udp_con.set_generic_callback(self.unknown_packet_callback)


        # Init Player
        player = Player()
        self.players.append(player)
        player_index = len(self.players) - 1

        setattr(packet_manager_tcp, "_player_index", player_index)
        setattr(udp_con, "_player_index", player_index)

        self.__addr_lookup[packet_manager_tcp.sock.getpeername()[0]] = player_index

        # Add connection tracking info
        self.connections.append([packet_manager_tcp, udp_con])

        return None

    def __update_networks(self):
        for tcp, udp in self.connections:
            tcp.update()

            if udp:
                udp.update()

    def __update_player_positions(self):
        player_info = self.__get_players_information()

        for tcp, udp in self.connections:
            udp.send("GlobalPlayerData", write_value(player_info))


    def run(self):
        """ Starts up the server, then runs a loop to allow connections"""
        threading.Thread(target=self.__startup, daemon=True).start()

        Log.log(f"Listening For Connections")
        self.sock.listen(5)

        while True:
            conn, addr = self.sock.accept()

            if len(self.players) < Server.MAX_PLAYERS:
                threading.Thread(target=self.__handle_client, args=(conn, addr), daemon=True).start()

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
        self.ping_start = -1
        self.error = None
        self.map_loaded = False

        self.target_tps = 60
        self.target_time = 1 / self.target_tps

        self.__tcp_callbacks = {
            b"pong": self.on_pong,
            b"map_data": self.on_recv_map_data,
            b"tps": self.on_recv_server_tps
        }

        self.tcp = None
        self.udp = None

        self.proxy_chat = ProxyChat(self.udp, read_value)

    @staticmethod
    def unknown_packet_callback(conn_manager, packet_type, data, protocol: str):
        Log.log(f"WARNING: CLIENT Unknown {protocol} Packet Type -> {packet_type}: {data[:500]}")

    def hook_render_engine(self):
        Log.log("Client hooked render engine")
        self.engine.client = self

    def __udp_callback(self, conn_manager):
        Log.log("Connected via UDP and TCP")
        self.udp: ConnectionUDP = Client_UDP_Handshake.get_udp_from_tcp(conn_manager)

        if not isinstance(self.udp, ConnectionUDP):
            raise ConnectionError("Failed to establish UDP")

        self.udp.add_packet_callback("GlobalPlayerData", self.on_player_info_update)

        self.proxy_chat.udp_conn = self.udp
        self.proxy_chat.on_udp_init()

        self.proxy_chat.start()

    def connect(self) -> bool | None | Any:
        """ Attempts to connect to the server, returns true / error message, if successful / failed"""
        self.sock.connect(self.address)

        self.tcp = ConnectionTCP(self.sock, self.__tcp_callbacks, self.unknown_packet_callback)
        Client_UDP_Handshake.enable_udp_creation(self.tcp, self.__udp_callback)

        Log.log(f"Server accepted client")

        self.get_map_data()
        self.get_server_tps()

        return True

    def disconnect(self) -> None:
        """ Safely disconnects from server """
        Log.log(f"Disconnecting...")
        self.tcp.send("disconnect", b"")
        self.sock.close()

        if self.udp:
            self.udp.sock.close()

    def ping(self) -> int | None:
        """ Returns time in ms or none if an invalid value is received"""
        self.ping_start = time.time()
        self.tcp.send("ping", b"")

    def on_pong(self, tcp_conn, data: bytes):
        self.current_ping = round((time.time() - self.ping_start) / 1000)

    def get_map_data(self):
        """ Gets the raw file data of the servers loaded map"""
        self.tcp.send("map_data", b"")

    def on_recv_map_data(self, tcp_conn, data: bytes):
        self.load_map(data)

    def get_server_tps(self):
        """ Gets the servers desired TPS"""
        self.tcp.send("tps", b"")

    def on_recv_server_tps(self, tcp_conn, data: bytes):
        self.target_tps = int.from_bytes(data, byteorder="big")
        self.target_time = 1 / self.target_tps

    def set_radio(self, is_on: bool):
        self.tcp.send("set_radio", b"1" if is_on else b"0")

    def update_player_info(self):
        """ Update the servers version of out data"""
        if self.udp is not None:
            self.udp.send("player_info", write_value(self.player.get_info()))

    def on_player_info_update(self, udp_conn, sender: tuple[str, int], data: bytes):
        """ Retrieves and updates all player data (including our own) """

        for player_info in read_value(data):  # NOQA - It should always be a list
            if player_info["username"] not in self.players:
                self.players[player_info["username"]] = Player()

            self.players[player_info["username"]].recv_info(player_info)


    def load_map(self, map_data):
        """ Loads the map data from the servers loaded map and loads it into render engine """
        Log.log(f"Received Map Data ({round(len(map_data) / 1024)}Kb)")
        path = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=5)) + "_temp_map.bin"

        try:
            with open(path, "wb") as f:
                f.write(map_data)

            self.engine.load_map(path)
            self.map_loaded = True
        except:
            os.remove(path)
            raise

        os.remove(path)

    def set_ready(self, ready_status: bool = True) -> None:
        """ Sets player status to "ready" allowing server to start playing """
        self.player.ready = ready_status

    def update_ping(self):
        if self.tcp is not None:
            self.ping()

    def update_network(self):
        self.update_player_info()

        if self.tcp is not None:
            self.tcp.update()

        if self.udp is not None:
            self.udp.update()


    def start(self) -> None:
        """ Handles all connections and data transfer, in the background"""
        self.hook_render_engine()

        try:
            result = self.connect()

            if result is not True:
                raise ConnectionRefusedError(result)

        except Exception as e:
            self.error = str(e)
            raise
