import inspect
import os
import time

ACTIVE_LOG_PATH = "log/latest.txt"


def copy(src, dst):
    with open(src, "rb") as f:
        data = f.read()

    with open(dst, "wb") as f:
        f.write(data)

class Log:
    LOG_START_TIME: int

    def load(self):
        with open(ACTIVE_LOG_PATH, "rb") as f:
            self.LOG_START_TIME = int.from_bytes(f.read(8), byteorder="little")


    def new(self):
        if not os.path.exists("log"):
            os.mkdir("log")

        if os.path.exists(ACTIVE_LOG_PATH):
            self.load()

            copy(ACTIVE_LOG_PATH, f"log/log_{self.LOG_START_TIME}.txt")
            os.remove(ACTIVE_LOG_PATH)

        self.LOG_START_TIME = round(time.time())

        with open(ACTIVE_LOG_PATH, "wb") as f:
            f.write(self.LOG_START_TIME.to_bytes(8, byteorder="little"))
            f.write(b"\n======= LOG START =======")

    @staticmethod
    def write(log_message):
        print(log_message)
        with open(ACTIVE_LOG_PATH, "a") as f:
            f.write(log_message + "\n")

    @staticmethod
    def log(msg):
        frame = inspect.currentframe().f_back
        info = inspect.getframeinfo(frame)

        path = os.path.normpath(info.filename)
        # Try to split at "engine"
        if "engine" in path:
            path = path.split("engine", 1)[1]  # keep everything after "engine"
            path = os.path.join("engine", path.lstrip(os.sep))
        else:
            # fallback to just the basename if "engine" not in path
            path = os.path.basename(path)

        log_message = f"[{path}:{info.function}] {msg}"
        Log.write(log_message)

