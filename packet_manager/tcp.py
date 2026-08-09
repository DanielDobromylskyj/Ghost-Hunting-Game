import socket
from typing import Callable

from .connection import Connection

class ConnectionTCP(Connection):
    def __init__(self, sock: socket.socket, callbacks: dict[bytes, Callable] | None = None,
                 generic_callback: None | Callable = None):
        super().__init__(sock, callbacks, generic_callback)

        self._recv_buffer = bytearray()
        self._send_buffer = bytearray()

    # TCP Receive/Read Helpers
    def __recv_exact(self, n: int):
        buf = bytearray(n)
        view = memoryview(buf)

        while n:
            received = self.sock.recv_into(view, n)

            if received == 0:
                self.on_connection_drop()  # Errors out / Stops read

            view = view[received:]
            n -= received

        return buf

    def __recv_uint64(self):
        return int.from_bytes(self.__recv_exact(8), "big")

    def __recv_variable(self):
        length = self.__recv_uint64()

        if length > 0:
            return self.__recv_exact(length)
        return b""

    def _process_recv_buffer(self):
        while True:
            # Need packet type length
            if len(self._recv_buffer) < 8:
                return

            type_len = int.from_bytes(self._recv_buffer[:8], "big")

            # Need packet type
            if len(self._recv_buffer) < 8 + type_len:
                return

            offset = 8

            packet_type = bytes(
                self._recv_buffer[offset:offset + type_len]
            )

            offset += type_len

            # Need payload length
            if len(self._recv_buffer) < offset + 8:
                return

            payload_len = int.from_bytes(
                self._recv_buffer[offset:offset + 8],
                "big"
            )

            offset += 8

            # Need payload
            if len(self._recv_buffer) < offset + payload_len:
                return

            payload = bytes(
                self._recv_buffer[offset:offset + payload_len]
            )

            offset += payload_len

            del self._recv_buffer[:offset]

            self.process_packet(packet_type, payload)

    def _process_inbound_messages(self):
        """ Checks for inbound packets and forwards them to the required callbacks"""
        while self.sock:
            try:
                data = self.sock.recv(4096)

                if not data:
                    raise ConnectionError("Socket closed")

                self._recv_buffer.extend(data)

            except (BlockingIOError, OSError):
                break

        self._process_recv_buffer()

    # Sending TCP Helpers
    def __queue_uint64(self, value: int):
        self._send_buffer += value.to_bytes(8, "big")

    def __queue_variable(self, data: bytes):
        self.__queue_uint64(len(data))
        self._send_buffer += data

    def _flush_send_buffer(self):
        while self._send_buffer:
            try:
                sent = self.sock.send(self._send_buffer)

                if sent == 0:
                    self.on_connection_drop()

                del self._send_buffer[:sent]

            except BlockingIOError:
                return

            except ConnectionError:
                self.on_connection_drop()

    def _send(self, packet_type: str, packet_data: bytes):
        self.__queue_variable(packet_type.encode("utf-8"))
        self.__queue_variable(packet_data)
        self._flush_send_buffer()