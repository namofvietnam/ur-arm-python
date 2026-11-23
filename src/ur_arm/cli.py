import argparse
import json
import os
import sys
from math import radians

from .robot import (
    DEFAULT_ACCELERATION_RAD_S2,
    DEFAULT_SPEED_RAD_S,
    Robot,
    validate_joint_move,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send Python RTDE commands to a Universal Robots arm", allow_abbrev=False
    )
    parser.add_argument(
        "--host", default=os.getenv("UR_HOST"), help="controller IP or hostname (or set UR_HOST)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="read current joint angles, TCP pose and controller modes")

    move = commands.add_parser(
        "movej", help="preview or execute a joint-space move", allow_abbrev=False
    )
    move.add_argument(
        "joints",
        metavar="JOINT",
        type=float,
        nargs=6,
        help="six target angles in base-to-wrist order, in radians",
    )
    move.add_argument("--degrees", action="store_true", help="interpret target angles in degrees")
    move.add_argument(
        "--speed", type=float, default=DEFAULT_SPEED_RAD_S, help="joint speed in rad/s (default %(default)s)"
    )
    move.add_argument(
        "--acceleration",
        type=float,
        default=DEFAULT_ACCELERATION_RAD_S2,
        help="joint acceleration in rad/s² (default %(default)s)",
    )
    move.add_argument(
        "--execute", action="store_true", help="connect to the controller and execute the move"
    )

    args = parser.parse_args(argv)
    if (args.command == "status" or args.execute) and not (args.host or "").strip():
        parser.error("provide --host before the command or set UR_HOST")

    try:
        if args.command == "status":
            result = Robot(args.host).status()
        else:
            joints = [radians(angle) for angle in args.joints] if args.degrees else args.joints
            joints = validate_joint_move(joints, args.speed, args.acceleration)
            if args.execute:
                Robot(args.host).move_j(
                    joints, speed_rad_s=args.speed, acceleration_rad_s2=args.acceleration
                )
            result = {
                "executed": args.execute,
                "target_joints_rad": joints,
                "speed_rad_s": args.speed,
                "acceleration_rad_s2": args.acceleration,
            }
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"ur-arm: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130

    print(json.dumps(result, indent=2))
    return 0
