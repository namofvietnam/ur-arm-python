"""Check the UR controller connection, read joints, or send a joint move."""

from __future__ import annotations

import argparse
import socket
import struct
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from math import degrees, dist, isfinite, radians

ROBOT_IP = "192.168.0.101"  # Enter the controller IP here, e.g. "192.168.0.10".
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


@contextmanager
def control_session(host: str):
    from rtde_control import RTDEControlInterface

    controller = RTDEControlInterface(host)
    try:
        yield controller
    finally:
        try:
            controller.stopScript()
        finally:
            controller.disconnect()


def move_j(host: str, target_rad: Sequence[float]) -> None:
    """Move to six joint angles in radians and wait for completion."""
    target = list(target_rad)
    if len(target) != 6 or not all(isfinite(angle) for angle in target):
        raise ValueError("Provide six finite joint angles")

    with control_session(host) as controller:
        if not controller.moveJ(target, 0.2, 0.3, False):
            raise RuntimeError("The controller did not report a completed joint move")


def read_tcp_pose(host: str) -> list[float]:
    from rtde_receive import RTDEReceiveInterface

    receiver = RTDEReceiveInterface(host, variables=["actual_TCP_pose"])
    try:
        pose = list(receiver.getActualTCPPose())
    finally:
        receiver.disconnect()

    if len(pose) != 6 or not all(isfinite(value) for value in pose):
        raise RuntimeError("The controller did not return a valid TCP pose")
    return pose


def move_x_5cm(host: str) -> None:
    """Move the TCP 5 cm along base +X, keeping its orientation fixed."""
    start = read_tcp_pose(host)
    target = start.copy()
    target[0] += 0.05

    with control_session(host) as controller:
        if not controller.moveL(target, 0.02, 0.05, False):
            raise RuntimeError("The controller did not report a completed X move")

    try:
        actual = read_tcp_pose(host)
    except (OSError, RuntimeError) as error:
        raise RuntimeError(f"Move reported complete, but TCP readback failed. {error}") from error
    displacement_cm = (actual[0] - start[0]) * 100
    position_error_mm = dist(actual[:3], target[:3]) * 1000
    if position_error_mm > 2:
        raise RuntimeError(
            f"TCP moved {displacement_cm:+.2f} cm along base X and is "
            f"{position_error_mm:.1f} mm from the target"
        )
    print(f"Move complete. Measured base X change {displacement_cm:+.2f} cm.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the UR10e Ethernet connection or send a joint command",
        epilog="Joint reading and motion require ur-rtde.",
        allow_abbrev=False,
    )
    parser.add_argument("host", nargs="?", help="override ROBOT_IP with a controller IP address")
    parser.add_argument("--sim", action="store_true", help="use the local simulator at 127.0.0.1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--joints", action="store_true", help="read the current joint angles in degrees")
    mode.add_argument("--move-x-5cm", action="store_true", help="move the tool 5 cm along base +X")
    mode.add_argument(
        "--move-deg",
        metavar="ANGLE",
        type=float,
        nargs=6,
        help="move to six verified joint angles in degrees, from base to wrist 3",
    )
    args = parser.parse_args(argv)

    if args.sim and args.host is not None:
        parser.error("--sim connects to 127.0.0.1. Omit the host argument.")
    host = "127.0.0.1" if args.sim else (args.host or ROBOT_IP).strip()
    if not host:
        parser.error("enter the controller's IP in ROBOT_IP at the top of this file or pass it as an argument")

    try:
        if args.move_x_5cm:
            move_x_5cm(host)
        elif args.move_deg is not None:
            move_j(host, [radians(angle) for angle in args.move_deg])
            print("Joint move complete.")
        elif args.joints:
            joints = read_joints(host)
            print("Current joint angles in degrees", [round(degrees(angle), 3) for angle in joints])
        else:
            check_connection(host)
    except ImportError as error:
        print(f"Could not load ur-rtde — {error}", file=sys.stderr)
        print("Install the dependency in your Python virtual environment with", file=sys.stderr)
        print("  python -m pip install -r requirements.txt", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"UR controller error for {host} — {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
