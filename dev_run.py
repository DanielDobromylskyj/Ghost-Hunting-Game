import subprocess
import time

server = subprocess.Popen([r"E:\Python\.venv1\Scripts\python.exe", "server_main.py"])

time.sleep(1)  # give server time to boot

client = subprocess.Popen([r"E:\Python\.venv1\Scripts\python.exe ", "main.py"])

try:
    client.wait()
finally:
    server.terminate()