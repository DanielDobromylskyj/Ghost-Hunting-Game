import sounddevice as sd
from collections import defaultdict, deque
import numpy as np

from .logger import Log
from packet_manager import ConnectionUDP

SAMPLE_RATE = 48000
CHANNELS = 1
BLOCKSIZE = 1024


class ProxyChat:

    def __init__(
        self,
        udp_conn: ConnectionUDP | None,
        decode_func,
        input_device=None,
        output_device=None
    ):
        self.udp_conn = udp_conn
        self.active = False
        self.init = False

        self.decode_func = decode_func

        self.audio_buffers = defaultdict(deque)

        self.input_stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCKSIZE,
            callback=self.input_callback,
            device=input_device
        )

        self.output_stream = sd.RawOutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCKSIZE,
            callback=self.output_callback_audio,
            device=output_device
        )



    def input_callback(self, indata, frames, time, status):
        if status:
            print("Input status:", status)

        audio = bytes(indata)

        if self.udp_conn is not None:
            self.udp_conn.send("ProxyVoiceToServer", audio)


    def output_callback_audio(self, outdata, frames, time, status):
        if status:
            print("Output status:", status)

        mix = None
        active = 0

        for queue in self.audio_buffers.values():
            if not queue:
                continue

            audio, volume, over_radio, rel_x, rel_y = queue.popleft()

            frame = (np.frombuffer(audio, dtype=np.int16) * volume).astype(np.int16)

            # Safety in case the received frame isn't exactly the requested size.
            if len(frame) != frames:
                continue

            if mix is None:
                mix = frame.astype(np.int32)
            else:
                mix += frame

            active += 1

        if mix is None:
            outdata[:] = b"\x00" * len(outdata)
            return

        mix //= active

        np.clip(
            mix,
            -32768,
            32767,
            out=mix
        )

        outdata[:] = mix.astype(np.int16).tobytes()



    def output_callback(self, udp_conn, sender, data: bytes):
        if not self.active:
            return

        decoded = self.decode_func(data)

        player = decoded["from"]
        audio = decoded["bytes"]

        self.audio_buffers[player].append((
            audio,
            decoded["vol"],
            decoded["radio"],
            decoded["rel_x"],
            decoded["rel_y"],
        ))



    def on_udp_init(self, *args):
        if self.udp_conn is None:
            raise ConnectionError(
                "Called on_udp_init before UDP has been created"
            )

        self.udp_conn.add_packet_callback(
            "ProxyVoiceToClient",
            self.output_callback,
            overwrite=True
        )

        self.init = True

        Log.log(
            "Initialized ProxyChat networking callback over UDP"
        )




    def start(self):
        if not self.init:
            self.on_udp_init()

        self.active = True

        self.input_stream.start()
        self.output_stream.start()

    def stop(self):
        self.active = False

        self.input_stream.stop()
        self.output_stream.stop()