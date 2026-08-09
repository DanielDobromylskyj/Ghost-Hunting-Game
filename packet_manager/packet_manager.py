from typing import Callable

class PacketManager:
    def __init__(self, callbacks: dict[bytes, Callable] | None, generic_callback: None | Callable):
        self.__callbacks: dict[bytes, Callable] = callbacks if isinstance(callbacks, dict) else {}
        self.__generic_callback = generic_callback

    def add_packet_callback(self, packet_type: str, callback: Callable, overwrite=False):
        if packet_type.encode('utf-8') in self.__callbacks and not overwrite:
            raise IndexError("Callback Already Hooked, Overwrite not enabled")

        self.__callbacks[packet_type.encode('utf-8')] = callback

    def remove_callback(self, packet_type: str):
        if packet_type.encode('utf-8') in self.__callbacks:
            self.__callbacks.pop(packet_type.encode('utf-8'))

    def set_generic_callback(self, callback: Callable):
        self.__generic_callback = callback

    def process_packet(self, packet_type: bytes, data: bytes, sender=None):
        if not isinstance(packet_type, bytes):
            packet_type = bytes(packet_type)

        if packet_type in self.__callbacks:
            callback = self.__callbacks[packet_type]

            if sender is None:
                return callback(self, data)
            else:
                return callback(self, sender, data)

        elif self.__generic_callback is not None:
            return self.__generic_callback(self, packet_type, data, protocol="UDP" if sender else "TCP")

        return None
