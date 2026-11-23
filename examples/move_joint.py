"""On URSim, add five degrees to the current wrist 3 position."""

import argparse
from math import radians

from ur_arm import Robot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--host", default="127.0.0.1", help="URSim controller address")
    parser.add_argument("--execute", action="store_true", help="send the move to URSim")
    args = parser.parse_args()

    robot = Robot(args.host)
    target = robot.status()["joint_positions_rad"]
    target[5] += radians(5)
    print(f"Target joints in radians: {target}")
    if args.execute:
        robot.move_j(target)
        print(f"Actual joints in radians: {robot.status()['joint_positions_rad']}")


if __name__ == "__main__":
    main()
