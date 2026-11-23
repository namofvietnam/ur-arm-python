"""Check the Ethernet connection and RTDE API using standard Python."""

import socket
import struct
import sys

ROBOT_IP = ""  # Enter the controller IP here, e.g. "192.168.0.10".
RTDE_PORT = 30004  # Standard Universal Robots RTDE API port.
TIMEOUT_SECONDS = 5

HEADER = struct.Struct(">HB")
REQUEST_PROTOCOL_VERSION = ord("V")
GET_CONTROLLER_VERSION = ord("v")


def request(connection, reader, command, reply_size, payload=b""):
    connection.sendall(HEADER.pack(HEADER.size + len(payload), command) + payload)
    expected_header = HEADER.pack(HEADER.size + reply_size, command)
    if reader.read(HEADER.size) != expected_header:
        raise RuntimeError(f"Unexpected RTDE reply to command {chr(command)}")
    reply = reader.read(reply_size)
    if len(reply) != reply_size:
        raise RuntimeError("The controller closed the connection during its RTDE reply")
    return reply


def main():
    host = ROBOT_IP.strip()
    if not host:
        print("Enter the controller's IP address in ROBOT_IP at the top of this file.", file=sys.stderr)
        return 2

    try:
        with socket.create_connection((host, RTDE_PORT), timeout=TIMEOUT_SECONDS) as connection:
            print(f"Connected over TCP to {host}:{RTDE_PORT}")
            with connection.makefile("rb") as reader:
                accepted = request(
                    connection, reader, REQUEST_PROTOCOL_VERSION, 1, struct.pack(">H", 2)
                )
                if accepted != b"\x01":
                    raise RuntimeError("The controller rejected RTDE protocol version 2")
                version = request(connection, reader, GET_CONTROLLER_VERSION, 16)
    except (OSError, RuntimeError) as error:
        print(f"Connection check failed for {host}:{RTDE_PORT} — {error}", file=sys.stderr)
        return 1

    major, minor, patch, build = struct.unpack(">IIII", version)
    print(f"RTDE API responded. Controller software version {major}.{minor}.{patch}.{build}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
