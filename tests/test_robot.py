import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from ur_arm import Robot
from ur_arm.cli import main


class RobotTests(unittest.TestCase):
    @patch("rtde_receive.RTDEReceiveInterface")
    def test_status_reads_controller_values(self, connect):
        receiver = connect.return_value
        receiver.getTimestamp.return_value = 12.5
        receiver.getActualQ.return_value = [0.1] * 6
        receiver.getActualTCPPose.return_value = [0.2] * 6
        receiver.getRobotMode.return_value = 7
        receiver.getSafetyMode.return_value = 1

        self.assertEqual(
            Robot("controller").status(),
            {
                "controller_timestamp_s": 12.5,
                "joint_positions_rad": [0.1] * 6,
                "tcp_pose": [0.2] * 6,
                "robot_mode": 7,
                "safety_mode": 1,
            },
        )
        receiver.disconnect.assert_called_once_with()

    @patch("rtde_receive.RTDEReceiveInterface")
    def test_status_reports_incomplete_frame_after_disconnection(self, connect):
        receiver = connect.return_value
        receiver.getActualQ.return_value = []
        receiver.getActualTCPPose.return_value = []

        with self.assertRaisesRegex(RuntimeError, "complete RTDE status"):
            Robot("controller").status()

        receiver.disconnect.assert_called_once_with()

    @patch("rtde_control.RTDEControlInterface")
    def test_move_rejects_invalid_input_before_connecting(self, connect):
        robot = Robot("controller")
        for joints in ([0] * 5, [float("nan")] * 6):
            with self.subTest(joints=joints), self.assertRaises(ValueError):
                robot.move_j(joints)
        with self.assertRaises(ValueError):
            robot.move_j([0] * 6, acceleration_rad_s2=0)
        connect.assert_not_called()

    @patch("rtde_control.RTDEControlInterface")
    def test_move_reports_failure_and_closes_control_session(self, connect):
        control = connect.return_value
        control.moveJ.return_value = False

        with self.assertRaisesRegex(RuntimeError, "successful joint move"):
            Robot("controller").move_j([0.1] * 6)

        connect.assert_called_once_with("controller")
        control.moveJ.assert_called_once_with([0.1] * 6, 0.2, 0.3, False)
        control.stopScript.assert_called_once_with()
        control.disconnect.assert_called_once_with()

    @patch("ur_arm.cli.Robot")
    def test_cli_previews_degrees_without_connecting(self, robot):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["movej", "--degrees", "0", "-90", "90", "0", "0", "0"])

        self.assertEqual(code, 0)
        preview = json.loads(output.getvalue())
        self.assertFalse(preview["executed"])
        self.assertAlmostEqual(preview["target_joints_rad"][1], -1.5707963267948966)
        robot.assert_not_called()
