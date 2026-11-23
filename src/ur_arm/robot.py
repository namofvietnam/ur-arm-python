from collections.abc import Sequence
from math import isfinite
from typing import TypedDict

DEFAULT_SPEED_RAD_S = 0.2
DEFAULT_ACCELERATION_RAD_S2 = 0.3


class RobotStatus(TypedDict):
    controller_timestamp_s: float
    joint_positions_rad: list[float]
    tcp_pose: list[float]
    robot_mode: int
    safety_mode: int


def validate_joint_move(
    joints_rad: Sequence[float], speed_rad_s: float, acceleration_rad_s2: float
) -> list[float]:
    if isinstance(joints_rad, (str, bytes)) or len(joints_rad) != 6:
        raise ValueError("Provide six joint positions in radians")
    joints = [float(position) for position in joints_rad]
    if not all(isfinite(position) for position in joints):
        raise ValueError("Each joint position must be finite")
    if not isfinite(speed_rad_s) or speed_rad_s <= 0:
        raise ValueError("Joint speed must be finite and positive")
    if not isfinite(acceleration_rad_s2) or acceleration_rad_s2 <= 0:
        raise ValueError("Joint acceleration must be finite and positive")
    return joints


class Robot:
    """An RTDE client for a Universal Robots controller or URSim instance."""

    def __init__(self, host: str) -> None:
        self.host = host.strip()
        if not self.host:
            raise ValueError("Provide the robot's IP address or hostname")

    def status(self) -> RobotStatus:
        """Read joint angles, TCP pose and controller modes without uploading a program."""
        from rtde_receive import RTDEReceiveInterface

        receiver = RTDEReceiveInterface(
            self.host,
            variables=["timestamp", "actual_q", "actual_TCP_pose", "robot_mode", "safety_mode"],
        )
        try:
            joint_positions = receiver.getActualQ()
            tcp_pose = receiver.getActualTCPPose()
            if len(joint_positions) != 6 or len(tcp_pose) != 6:
                raise RuntimeError(f"Controller at {self.host} did not return a complete RTDE status")
            return {
                "controller_timestamp_s": receiver.getTimestamp(),
                "joint_positions_rad": joint_positions,
                "tcp_pose": tcp_pose,
                "robot_mode": receiver.getRobotMode(),
                "safety_mode": receiver.getSafetyMode(),
            }
        finally:
            receiver.disconnect()

    def move_j(
        self,
        joints_rad: Sequence[float],
        *,
        speed_rad_s: float = DEFAULT_SPEED_RAD_S,
        acceleration_rad_s2: float = DEFAULT_ACCELERATION_RAD_S2,
    ) -> None:
        """Send a joint-space move and wait for the controller to report completion."""
        joints = validate_joint_move(joints_rad, speed_rad_s, acceleration_rad_s2)

        from rtde_control import RTDEControlInterface

        control = RTDEControlInterface(self.host)
        try:
            if not control.moveJ(joints, speed_rad_s, acceleration_rad_s2, False):
                raise RuntimeError("Controller did not report a successful joint move")
        finally:
            try:
                control.stopScript()
            finally:
                control.disconnect()
