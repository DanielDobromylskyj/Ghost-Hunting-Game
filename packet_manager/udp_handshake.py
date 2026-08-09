import socket

from typing import Callable

from .tcp import ConnectionTCP
from .udp import ConnectionUDP
from .connection import createUDPsocket


class Client:
    @staticmethod
    def __on_udp_creation_request(tcp_conn: ConnectionTCP, data: bytes):
        ip = ".".join([str(byte) for byte in list(data[:4])])
        port = int.from_bytes(data[4:8], byteorder="big")

        udp_socket = createUDPsocket()
        udp_socket.connect((ip, port))

        udp_conn = ConnectionUDP(udp_socket, (ip, port))
        udp_conn.send("_UDP:Handshake", b"OK")

        setattr(tcp_conn, "_udp_conn", udp_conn)

        if hasattr(tcp_conn, "_udp_request_callback"):
            getattr(tcp_conn, "_udp_request_callback")(tcp_conn)

    @staticmethod
    def get_udp_from_tcp(tcp_conn):
        if hasattr(tcp_conn, "_udp_conn"):
            return getattr(tcp_conn, "_udp_conn")
        return None

    @staticmethod
    def enable_udp_creation(tcp_connection: ConnectionTCP, callback: Callable | None = None):
        tcp_connection.add_packet_callback(
            "_TCP:Request_UDP",
            Client.__on_udp_creation_request,
            overwrite=True
        )

        if callback:
            setattr(tcp_connection, "_udp_request_callback", callback)


class PeerServer:
    @staticmethod
    def __on_udp_handshake(udp_conn: ConnectionUDP, sender_addr: tuple[str, int], data):
        if data != b"OK":
            raise ValueError("Invalid data sent on UDP Handshake packet!")

        #udp_conn.target_addr = sender_addr
        #udp_conn.remove_callback('_UDP:Handshake')
        print(udp_conn)

    @staticmethod
    def request_udp_connection(tcp_connection: ConnectionTCP, udp_socket: socket.socket):
        server_ip, port = udp_socket.getsockname()
        client_ip, p = tcp_connection.sock.getpeername()

        print("Server:", server_ip, port)
        print("Client:", client_ip, p)

        udp_connection = ConnectionUDP(udp_socket, (client_ip, port))
        udp_connection.add_packet_callback("_UDP:Handshake", PeerServer.__on_udp_handshake, overwrite=True)

        addr_bytes = bytes(int(chunk) for chunk in server_ip.split(".")) + port.to_bytes(4, byteorder="big")

        tcp_connection.send("_TCP:Request_UDP", addr_bytes)

        return udp_connection