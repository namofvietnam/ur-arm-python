import argparse
import sys
from collections.abc import Sequence
from math import degrees, isfinite, radians


def read_joints(host: str) -> list[float]:
    """Read the six current joint angles in radians."""
    from rtde_receive import RTDEReceiveInterface

    receiver = RTDEReceiveInterface(host, variables=["actual_q"])
    try:
        return receiver.getActualQ()
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a joint command to a UR10e", allow_abbrev=False)
    parser.add_argument("host", help="IP address of the UR controller")
    parser.add_argument(
        "--move-deg",
        metavar="ANGLE",
        type=float,
        nargs=6,
        help="execute a move to six joint angles in degrees, from base to wrist 3",
    )
    args = parser.parse_args()

    try:
        if args.move_deg is None:
            joints = read_joints(args.host)
            print("Current joint angles in degrees", [round(degrees(angle), 3) for angle in joints])
        else:
            move_j(args.host, [radians(angle) for angle in args.move_deg])
            print("Joint move complete.")
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"UR controller error — {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
