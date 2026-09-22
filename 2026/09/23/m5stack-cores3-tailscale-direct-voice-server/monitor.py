"""Capture USB serial logs without toggling the board's DTR/RTS reset lines."""
import argparse
import sys
import time
from pathlib import Path

import serial

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser()
parser.add_argument("port")
parser.add_argument("--seconds", type=int, default=600)
parser.add_argument("--log", type=Path, default=Path("serial-probe.log"))
args = parser.parse_args()
deadline = time.monotonic() + args.seconds
with args.log.open("a", encoding="utf-8") as log:
    while time.monotonic() < deadline:
        device = serial.Serial()
        device.port = args.port
        device.baudrate = 115200
        device.timeout = 1
        device.dtr = False
        device.rts = False
        try:
            device.open()
            while time.monotonic() < deadline:
                data = device.readline()
                if not data:
                    continue
                line = data.decode("utf-8", errors="replace")
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
        except serial.SerialException as error:
            print(f"Serial reconnect: {error}", flush=True)
            time.sleep(1)
        finally:
            device.close()
