# PICO Teleop

Unified VR teleoperation platform for multi-configuration dual-arm robots using WebSocket-based communication between server and robot.

## Architecture

```
+------------------------------------------------------------------+
|  PICO VR (Browser)                                               |
|  WebXR + Three.js                                                |
|  React + Ant Design                                              |
+------------------------------------------------------------------+
       | HTTPS :3000
       v
+------------------------------------------------------------------+
|  SERVER (Docker)                                                 |
|  +------------------------------------------------------------+  |
|  | Web Frontend (Node.js)                                     |  |
|  | - Serves React app at :3000                                |  |
|  | - WebSocket relay for VR input                             |  |
|  +------------------------------------------------------------+  |
|  +------------------------------------------------------------+  |
|  | ROS2 Components (retarget, IK, server_bridge)             |  |
|  | - Receives VR controller poses                             |  |
|  | - Computes inverse kinematics (cuRobo/TRAC-IK/MoveIt)      |  |
|  | - Publishes joint commands via WebSocket :38270             |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
       | WebSocket :38270
       | (No cross-machine ROS2)
       v
+------------------------------------------------------------------+
|  ROBOT (Docker, on robot machine)                                |
|  +------------------------------------------------------------+  |
|  | Pure Python - No ROS2                                      |  |
|  | - bridge.py: WebSocket client, receives joint commands     |  |
|  | - driver.py: Low-level arm control                         |  |
|  | - data_recorder.py: LeRobot format recording              |  |
|  +------------------------------------------------------------+  |
|  Cameras (USB) ---------> LeRobot Data Recorder                 |
+------------------------------------------------------------------+
```

## Quick Start

### Server Machine

```bash
# Start server (web frontend + ROS2 backend)
docker compose -f docker/docker-compose.yaml up
```

### Robot Machine

```bash
# Start robot bridge (connects to server via WebSocket)
docker compose -f docker/docker-compose.robot.yaml up
```

### PICO Headset

Open `https://SERVER_IP:3000` in the browser. Use VR controllers to teleoperate.

## Supported Arms

| Robot | Type | DoF | Status |
|-------|------|-----|--------|
| Unitree G1 | Dual | 7+7 | Config ready |
| Limix OLI | Dual | TBD | Planned |
| AGX Lift | Dual | TBD | Planned |
| Hans (Big Clan) | Dual | TBD | Planned |
| Franka Panda | Single | 7 | Config ready |
| Isaac Sim | Any | Any | Config ready |

## IK Solvers

Switch at runtime via frontend panel or service call:

| Solver | Backend | Latency | Collision Avoidance |
|--------|---------|---------|---------------------|
| TRAC-IK | CPU | ~1-5ms | No |
| cuRobo | GPU (CUDA) | ~5-10ms | Yes |
| MoveIt2 | CPU | 5-20ms | Yes (with planning scene) |

```bash
ros2 service call /teleop/switch_ik_solver pico_teleop_msgs/srv/SwitchIKSolver "{solver_name: 'curobo'}"
```

## Data Collection

Record teleoperation data in LeRobot format for imitation learning.

### Directory Structure

```
data/
  episode_XXXXX/
    state.npy         # Joint states (N x num_dof)
    action.npy        # Actions applied (N x num_dof)
    velocity.npy      # Joint velocities (N x num_dof)
    gripper.npy       # Gripper states (N x 1)
    timestamps.npy    # Unix timestamps (N)
    camera_0/
      frame_XXXXX.jpg # Camera frames
    camera_1/
      frame_XXXXX.jpg
    ...
  episode_XXXXX/
    ...
```

### Meta Files

```
data/
  meta/
    info.json         # Dataset metadata (robot config, camera params)
    episodes.jsonl    # One JSON entry per episode with duration, final return
```

### Start/Stop Recording

- **VR Button**: Press the grip button on either controller to start/stop recording
- **Web UI**: Use the recording controls in the frontend panel

Recording automatically saves to the `data/` directory mounted on the robot container.

## Adding a New Arm

1. Create `src/pico_teleop_bringup/config/arms/<arm_name>.yaml`
2. Add URDF to `src/pico_teleop_web/public/urdf/`
3. Implement `BaseArmDriver` subclass if non-standard interface
4. Add entry to frontend `ARM_OPTIONS` in `ControlPanel.tsx`

## Development

### ROS2 Backend (Server)

```bash
# Inside server container
colcon build --symlink-install
source install/setup.bash
ros2 launch pico_teleop_bringup teleop.launch.py arm_config:=franka_single ik_solver:=trac_ik
```

### Frontend (Server)

```bash
# On host or container
cd src/pico_teleop_web
npm install
npm run dev
```

### Robot (Pure Python)

```bash
# On robot machine
cd src/pico_teleop_robot
pip install -e .
pico-robot --server-url ws://SERVER_IP:38270 --cameras 0 1 --data-dir ./data
```

## Project Structure

```
src/
├── pico_teleop_msgs/           # Custom ROS2 messages & services
├── pico_teleop_core/          # Pipeline nodes (retarget, IK, dispatcher)
├── pico_teleop_drivers/       # Arm driver abstraction layer
├── pico_teleop_bringup/       # Launch files & arm configs
├── pico_teleop_web/           # React + WebXR frontend
└── pico_teleop_robot/         # Robot-side Python (bridge, driver, recorder)
    ├── bridge.py              # WebSocket client
    ├── driver.py              # Low-level arm control
    ├── data_recorder.py       # LeRobot format recording
    └── main.py                # Entry point
```

## License

MIT
