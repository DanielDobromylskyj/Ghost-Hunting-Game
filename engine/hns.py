# Host Network Starter (.py)

"""
- Run on the HOST (the person who sets the tunnel).
- Starts a simple TCP echo server on localhost.
- Spins up an ngrok tunnel to that local TCP port.
- Prints the public ngrok address (tcp://host:port) that a remote client can use.
"""

import subprocess
import sys
import time
import urllib.request
import json
from contextlib import contextmanager

NGROK_API = "http://127.0.0.1:4040/api/tunnels"

@contextmanager
def NgrokTunnel(port: int, proto: str = "tcp", extra_args=None):
    """
    Start an ngrok tunnel (tcp or http) forwarding to `port`.
    Yields a dict describing the tunnel (including public_url).
    Requires `ngrok` binary in PATH.

    Example:
        with NgrokTunnel(5000, proto="tcp") as info:
            print(info["public_url"])
    """
    extra_args = extra_args or []
    if proto not in ("tcp", "http"):
        raise ValueError("proto must be 'tcp' or 'http'")

    # Build ngrok command
    cmd = ["ngrok", proto, str(port)] + list(extra_args)
    print(f"[ngrok] starting: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        for i in range(30):  # ~30s max wait
            try:
                with urllib.request.urlopen(NGROK_API, timeout=1) as r:
                    data = json.load(r)

                    for t in data.get("tunnels", []):
                        public_url = t.get("public_url") or t.get("public_addr") or t.get("uri")
                        # For tcp tunnels public_url looks like tcp://x.tcp.ngrok.io:xxxxx
                        if public_url and (proto in public_url.lower()):
                            yield {"public_url": public_url, "details": t}
                            break

                    else:
                        pass

                    # if we yielded inside loop we'd have returned; if not, continue waiting
            except Exception:
                pass
            time.sleep(1)

        # If we get here, the tunnel didn't show up in time
        raise RuntimeError("ngrok did not expose the tunnel in time. Check ngrok is installed and authenticated.")
    finally:
        print("[ngrok] terminating ngrok process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def run_server(server_function, local_port, *args, **kwargs):
    LOCAL_PORT = local_port
    print("Starting ngrok TCP tunnel to local port", LOCAL_PORT)

    try:
        with NgrokTunnel(LOCAL_PORT, proto="tcp") as info:
            public = info["public_url"]
            print("\n=== SHARE THIS WITH YOUR FRIENDS ===")
            print(public)
            print("=================================\n")

            server_function(*args, **kwargs)
    except Exception as e:
        print("Error launching ngrok tunnel:", e)
        print("Troubleshooting tips:")
        print("- Ensure `ngrok` is installed and in PATH.")
        print("- If TCP tunnels are blocked for free accounts, try `proto='http'` and use an HTTP/websocket client instead.")
        sys.exit(1)

