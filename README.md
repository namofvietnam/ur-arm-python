# UR10e Python commands

Send a joint move to a UR10e running PolyScope 5. `send_move.py` uses the controller's RTDE interface over Ethernet.

## Read the arm first

From the repo folder, using Python 3.10 or newer in your virtual environment, run these commands. Replace `ROBOT_IP` with the controller's IP address. The first controller command reads the six joint angles in degrees.

```bash
python -m pip install -r requirements.txt
python send_move.py ROBOT_IP
```

Your computer needs network access to RTDE on TCP 30004. In PolyScope, check **Settings → Security → Services** if that service is disabled.

## Send one joint move

On the pendant, enable **Settings → System → Remote Control**, then select **Remote Control** in the top bar. The controller should be idle, powered on, and initialized with the brakes released. Motion also uses the Dashboard Server on TCP 29999 and Secondary Client Interface on TCP 30002.

Replace `J1` through `J6` with a nearby target in degrees, ordered from base to wrist 3. Verify the target and the path at the pendant with the workcell clear before sending the command. This uploads a temporary control script and can interrupt another running program.

```bash
python send_move.py ROBOT_IP --move-deg J1 J2 J3 J4 J5 J6
```

From your own Python code, import `read_joints` and `move_j` from `send_move`. Both functions use radians. The move runs at 0.2 rad/s with 0.3 rad/s² acceleration and waits for the controller to report completion.

[UR controller setup](https://sdurobotics.gitlab.io/ur_rtde/pages/getting_started/environment_setup.html#real-robot-setup)
