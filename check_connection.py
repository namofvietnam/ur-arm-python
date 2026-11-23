"""Check the UR controller connection, read joints, or send a joint move."""

from __future__ import annotations

import argparse
import socket
import struct
import sys
from collections.abc import Sequence
from math import degrees, isfinite, radians

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


def check_connection(host: str) -> None:
    with socket.create_connection((host, RTDE_PORT), timeout=TIMEOUT_SECONDS) as connection:
        print(f"Connected over TCP to {host}:{RTDE_PORT}")
        with connection.makefile("rb") as reader:
            accepted = request(connection, reader, REQUEST_PROTOCOL_VERSION, 1, struct.pack(">H", 2))
            if accepted != b"\x01":
                raise RuntimeError("The controller rejected RTDE protocol version 2")
            version = request(connection, reader, GET_CONTROLLER_VERSION, 16)

    major, minor, patch, build = struct.unpack(">IIII", version)
    print(f"RTDE API responded. Controller software version {major}.{minor}.{patch}.{build}")


def read_joints(host: str) -> list[float]:
    """Read the six current joint angles in radians."""
    from rtde_receive import RTDEReceiveInterface

    receiver = RTDEReceiveInterface(host, variables=["actual_q"])
    try:
        joints = receiver.getActualQ()
        if len(joints) != 6:
            raise RuntimeError("The controller did not return all six joint angles")
        return joints
    finally:
        receiver.disconnect()


def move_j(host: str, target_rad: Sequence[float]) -> None:
    """Move to six joint angles in radians and wait for completion."""
    target = list(target_rad)
    if len(target) != 6 or not all(isfinite(angle) for angle in target):
        raise ValueError("Provide six finite joint angles")

    from rtde_control import RTDEControlInterface

    controller = RTDEControlInterface(host)
    try:
        if not controller.moveJ(target, 0.2, 0.3, False):
            raise RuntimeError("The controller did not report a completed joint move")
    finally:
        try:
            controller.stopScript()
        finally:
            controller.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the UR10e Ethernet connection or send a joint command",
        epilog="Joint reading and motion require ur-rtde.",
        allow_abbrev=False,
    )
    parser.add_argument("host", nargs="?", help="override ROBOT_IP with a controller IP address")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--joints", action="store_true", help="read the current joint angles in degrees")
    mode.add_argument(
        "--move-deg",
        metavar="ANGLE",
        type=float,
        nargs=6,
        help="move to six verified joint angles in degrees, from base to wrist 3",
    )
    args = parser.parse_args(argv)

    host = (args.host or ROBOT_IP).strip()
    if not host:
        parser.error("enter the controller's IP in ROBOT_IP at the top of this file or pass it as an argument")

    try:
        if args.move_deg is not None:
            move_j(host, [radians(angle) for angle in args.move_deg])
            print("Joint move complete.")
        elif args.joints:
            joints = read_joints(host)
            print("Current joint angles in degrees", [round(degrees(angle), 3) for angle in joints])
        else:
            check_connection(host)
    except ImportError as error:
        print(f"Could not load ur-rtde — {error}", file=sys.stderr)
        print("Install the dependency in your WSL Ubuntu virtual environment with", file=sys.stderr)
        print("  python -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"UR controller error for {host} — {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
