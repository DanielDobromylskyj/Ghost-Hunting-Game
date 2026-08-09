import socket

from typing import Callable

from .packet_manager import PacketManager
from .exceptions import ConnectionDroppedError


def createTCPsocket():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def createUDPsocket():
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class Connection(PacketManager):
    def __init__(self, sock: socket.socket, callbacks: dict[bytes, Callable] | None =None, generic_callback: None | Callable = None):
        super().__init__(callbacks, generic_callback)

        self.sock = sock
        self.sock.setblocking(False)

        self.__connection_drop_callback: None | Callable = None

    def set_connection_drop_callback(self, callback: Callable):
        """ Set a function to be called when the Connection gets dropped """
        self.__connection_drop_callback = callback

    def on_connection_drop(self):
        """ Calls the connection dropped callback if required, then raises a 'ConnectionDroppedError' to exit """
        if self.__connection_drop_callback is not None:
            self.__connection_drop_callback()

        raise ConnectionDroppedError

    def _send(self, packet_type: str, packet_data: bytes):
        raise NotImplemented

    def send(self, packet_type: str, packet_data: bytes):
        try:
            self._send(packet_type, packet_data)
        except ConnectionDroppedError:
            pass

    def _process_inbound_messages(self):
        raise NotImplemented

    def process_inbound_messages(self):
        try:
            self._process_inbound_messages()
        except ConnectionDroppedError:
            pass

    def update(self):
        """ Legacy Function. Renamed to 'process_inbound_messages' for clarity """
        self.process_inbound_messages()
