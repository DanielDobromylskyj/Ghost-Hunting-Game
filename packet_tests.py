from packet_manager import *
from packet_manager import udp_handshake
import threading
import time

"""

Test file for my networking module

"""

def loop_function(func, interval: int | float, timeout: int | float):
    start = time.time()
    while (time.time() - start) < timeout:
        func()
        time.sleep(interval)

def echo_callback(*args):
    if len(args) == 3:
        _, __, data = args

    elif len(args) == 2:
        _, data = args

    else:
        print("BAD ECHO FORMAT")
        return

    print(data)

def server():
    # Create Sockets
    tcp_sock = createTCPsocket()
    tcp_sock.bind(('127.0.0.1', 6969))

    udp_sock = createUDPsocket()
    udp_sock.bind(('127.0.0.1', 6970))

    # Listen for client
    tcp_sock.listen(1)

    # Establish PacketManager Connection
    conn, _ = tcp_sock.accept()
    tcp_pkm = ConnectionTCP(conn)

    udp_pkm = udp_handshake.PeerServer.request_udp_connection(tcp_pkm, udp_sock)
    udp_pkm.add_packet_callback('test_echo', echo_callback)

    loop_function(udp_pkm.process_inbound_messages, 0.1, 2)

    udp_pkm.send('test_echo', b"From Server")


def client():
    tcp_sock = createTCPsocket()
    tcp_sock.connect(('127.0.0.1', 6969))

    tcp_pkm = ConnectionTCP(tcp_sock)

    udp_handshake.Client.enable_udp_creation(tcp_pkm)

    loop_function(tcp_pkm.process_inbound_messages, 0.1, 1)

    udp_pkm = udp_handshake.Client.get_udp_from_tcp(tcp_pkm)

    if not udp_pkm:
        print("[CLIENT] Did not get UDP connection in time!")
        raise Exception

    udp_pkm.add_packet_callback('test_echo', echo_callback)
    udp_pkm.send('test_echo', b"From Client")

    loop_function(udp_pkm.process_inbound_messages, 0.1, 2)


threading.Thread(target=server).start()
client()