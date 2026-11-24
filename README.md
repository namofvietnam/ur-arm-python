# UR10e Python control

Read joint positions, TCP pose and controller modes, or send a joint move from Python or the `ur-arm` CLI. The client uses RTDE and targets the UR10e with PolyScope 5 and the matching e-Series URSim simulator.

## Install

Use Python 3.12 on a 64-bit Intel or AMD machine. The pinned `ur-rtde` release provides wheels for Linux and native Windows. You can also use WSL Ubuntu on Windows. [Published wheels for ur-rtde 1.6.5](https://pypi.org/project/ur-rtde/1.6.5/#files)

Run these commands from the repo folder in a Linux terminal.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=ur-rtde -e .
```

For native Windows PowerShell, create and activate a Python 3.12 virtual environment, then install the requirements:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --only-binary=ur-rtde -e .
```

### Windows and VS Code

In PowerShell, use `wsl --list --online` to check the available distro names. If WSL Ubuntu is missing and the list shows `Ubuntu`, install it with `wsl --install -d Ubuntu`. Use the exact listed name if you choose a versioned distro.

Open Ubuntu and run `sudo apt update` followed by `sudo apt install -y python3-venv`. Change into the repo folder from Ubuntu. A Windows checkout at `C:\Users\<username>\Desktop\ur-arm-python` is visible at `/mnt/c/Users/<username>/Desktop/ur-arm-python`. Create the Linux venv as shown above. If you already use `.venv` for Windows Python, create and activate `.venv-wsl` for Linux.

Install Microsoft's WSL extension in VS Code and run `code .` from the Ubuntu terminal. In the WSL window, select `.venv/bin/python` or `.venv-wsl/bin/python` using **Python: Select Interpreter**. [VS Code WSL guide](https://code.visualstudio.com/docs/remote/wsl)

## Test movement at home in URSim

Start Docker Desktop in Linux containers mode on Windows. Use the VS Code PowerShell terminal with your Windows Python venv active so Python and Docker use the same localhost. From the repo folder, start the virtual UR10e with PolyScope 5.13.1.

```bash
docker compose up -d ursim
```

1. Open [the simulator UI](http://127.0.0.1:6080/vnc.html) and connect. Confirm the safety configuration if prompted, then power on the simulated arm and press **Start** on the initialization screen.
2. In PolyScope, enable **Settings → System → Remote Control**, then select **Remote Control** in the upper-right mode menu. Under **Settings → Security → Services**, enable RTDE for status and the Dashboard Server and Real-time Interface for motion if they are disabled.
3. With your Python venv active, check the connection, read the joints, and run the 5 cm move.

```bash
python check_connection.py --sim
python check_connection.py --sim --joints
python check_connection.py --sim --move-x-5cm
```

`--sim` connects to `127.0.0.1` regardless of the saved `ROBOT_IP`. The last command moves the tool 5 cm along the robot base's positive X axis at 2 cm/s and prints the displacement measured through RTDE. Each invocation uses the current pose. Reset the pose in the simulator before repeating if the arm is near a travel limit.

For joint-space motion, this example adds five degrees to the last joint.

```bash
python examples/move_joint.py --execute
```

Stop the simulator with `docker compose stop ursim`.

### PolyScope X 10.12.1 option

This profile uses Universal Robots' matching simulator image for the `10.12.1.0` controller. The vendor's image runs in privileged mode. The two simulators share the localhost RTDE ports, so stop the first before starting the second. [Universal Robots PolyScope X simulator](https://hub.docker.com/r/universalrobots/ursim_polyscopex)

```bash
docker compose stop ursim
docker compose up -d ursim-x
```

Open `http://127.0.0.1:6081`, initialize the virtual arm, and enable RTDE and the controller services needed for remote scripting under **Settings → Security → Services**. Run `python check_connection.py --sim` first and confirm the version is `10.12.1` before attempting the move above. The movement workflow was verified on the PolyScope 5 simulator. PolyScope X motion still needs its own verification.

## Send commands

`--host` accepts a controller IP address or hostname. You can also set `UR_HOST` for the CLI. The status includes six joint angles in radians, the TCP pose `[x, y, z, rx, ry, rz]` in meters and a rotation vector in radians, and the controller's numeric robot and safety modes.

```bash
ur-arm --host ROBOT_IP status
```

The quick-start script `python send_move.py ROBOT_IP` reads joint angles in degrees. Its `--move-deg` option accepts six target angles, from the base joint through wrist 3.

Preview an absolute joint target without connecting. The six values are ordered from the base joint through wrist 3.

```bash
ur-arm movej --degrees 0 -90 90 -90 -90 0
```

For execution, supply a target you have verified for the current arm configuration, its full motion path, and the workcell. `--speed` and `--acceleration` use rad/s and rad/s², including when `--degrees` is set.

```bash
ur-arm --host ROBOT_IP movej --degrees --execute J1 J2 J3 J4 J5 J6
```

Import `Robot` to use the same interface from your own Python code.

```python
from ur_arm import Robot

robot = Robot("127.0.0.1")  # URSim on this machine
status = robot.status()
print(status["joint_positions_rad"])

# Pass six verified joint targets in radians to send a move.
# robot.move_j(target_joints_rad, speed_rad_s=0.2, acceleration_rad_s2=0.3)
```

`Robot.move_j()` waits for the controller's result. It opens a motion session that uploads a temporary URScript program and may stop a running program. Run motion commands with the controller idle and one control client active. For hardware commissioning, verify the programmed payload, TCP, path and clearance with the operator before executing commands.

If status cannot connect, check the controller address and RTDE on TCP 30004. For motion, also check the remote profile, that the robot is powered with brakes released, and access to the Dashboard Server (TCP 29999) and Real-time Interface (TCP 30003). If a move reports an error, read the current state before deciding whether to send another command.

## Tests

```bash
python -m unittest discover -s tests -v
```

[Universal Robots RTDE guide](https://docs.universal-robots.com/tutorials/communication-protocol-tutorials/rtde-guide.html) · [ur-rtde environment setup](https://sdurobotics.gitlab.io/ur_rtde/pages/getting_started/environment_setup.html)
