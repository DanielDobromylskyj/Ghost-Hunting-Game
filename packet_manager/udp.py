import socket
from typing import Callable

from .connection import Connection

class ConnectionUDP(Connection):
    def __init__(self, sock: socket.socket, target: tuple[str, int], callbacks: dict[bytes, Callable] | None = None,
                 generic_callback: None | Callable = None):
        super().__init__(sock, callbacks, generic_callback)
        self.target_addr = target

    def _pre_packet_processing(self, packet_type, packet_bytes, sender):
        self.process_packet(packet_type, packet_bytes, sender)

    def _process_inbound_messages(self):
        """ Checks for inbound packets and forwards them to the required callbacks"""
        while self.sock:
            try:
                data, sender_addr = self.sock.recvfrom(65535)

                packet_type_len = int.from_bytes(data[:8], byteorder="big")
                packet_type = data[8:8 + packet_type_len]

                packet_bytes_len = int.from_bytes(data[8 + packet_type_len:16 + packet_type_len], byteorder="big")
                packet_bytes = data[16 + packet_type_len:16 + packet_type_len + packet_bytes_len]
                self._pre_packet_processing(packet_type, packet_bytes, sender=sender_addr)

            except (ConnectionAbortedError, ConnectionResetError):
                self.on_connection_drop()

            except (BlockingIOError, OSError):
                return  # No data available

    @staticmethod
    def __length_as_bytes(data) -> bytes:
        return len(data).to_bytes(8, byteorder="big")

    def _send(self, packet_type: str, packet_data: bytes):
        if self.target_addr == ("", 0):
            return

        packet_bytes = self.__length_as_bytes(packet_type) + packet_type.encode('utf-8') + self.__length_as_bytes(packet_data) + packet_data

        try:
            self.sock.sendto(packet_bytes, self.target_addr)

        except (ConnectionAbortedError, ConnectionResetError):
            self.on_connection_drop()

        except OSError:
            print(f"Failed to send packet '{packet_type}' of size {len(packet_bytes)} bytes. Data size: {len(packet_data)}")
            raise
            self.on_connection_drop()

