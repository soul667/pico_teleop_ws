# Robot SDK/Driver Reference

## Unitree G1

- **SDK**: https://github.com/unitreerobotics/unitree_sdk2_python
- **ROS2**: https://github.com/unitreerobotics/unitree_ros2
- **Protocol**: CycloneDDS (DDS middleware)
- **Arm DoF**: 7 per arm (14 total)
- **Control**: `unitree_sdk2_python` → position/torque hybrid mode
- **Install**: `pip install unitree-sdk2-python`
- **Teleop examples**: https://github.com/unitreerobotics/avp_teleoperate (Apple Vision Pro)

## LimX Dynamics OLI

- **SDK**: https://github.com/limxdynamics/limxsdk-lowlevel
- **ROS2**: https://github.com/limxdynamics/humanoid-rl-deploy-ros2
- **URDF**: https://github.com/limxdynamics/humanoid-description
- **Protocol**: Custom binary over Ethernet, 1000Hz control loop
- **Arm DoF**: 7 per arm (31 DoF total humanoid)
- **Control modes**: Position (mode 2), Velocity (mode 1), Torque-position hybrid (mode 0)
- **API**:
  ```cpp
  RobotCmd { stamp, mode[], q[], dq[], tau[], Kp[], Kd[] }
  RobotState { stamp, tau[], q[], dq[], motor_names[] }
  ```
- **License**: Apache 2.0

## Franka Emika (Panda / FR3)

- **Best for teleop**: `franky` (Ruckig trajectory + async streaming)
  - Install: `pip install franky-control`
  - Async: `robot.move(JointMotion(q), asynchronous=True)`
- **Low-level 1kHz**: `pylibfranka`
  - Install: `pip install pylibfranka`
  - 50Hz async position streaming via `start_joint_position_control()`
- **ROS2**: https://github.com/frankaemika/franka_ros2
- **Protocol**: libfranka over Ethernet (dedicated RT network)
- **Arm DoF**: 7
- **FR3 vs Panda**: Same API, FR3 has `robot_type: fr3` param, longer reach (950mm vs 855mm)

## Hans Robot (大族 Elfin)

- **ROS1**: https://github.com/hans-robot/elfin_robot
- **ROS2**: https://github.com/hans-robot/elfin_robot_ros2
- **Protocol**: Ethernet TCP (Modbus TCP for I/O, custom TCP for motion)
- **Series**: Elfin3, Elfin5, Elfin10 (3/5/10 kg payload)
- **Arm DoF**: 6
- **Control**: Position streaming via TCP socket, ~125Hz update rate
- **MoveIt**: Supported (elfin_robot_ros2 includes MoveIt2 config)

## AGX / Agilex Lift

- **Company**: AgileX Robotics (松灵机器人)
- **GitHub**: https://github.com/agilexrobotics
- **SDK**: https://github.com/agilexrobotics/ugv_sdk (CAN-based)
- **ROS2**: https://github.com/agilexrobotics/agilex_ros2
- **Protocol**: CAN bus for mobile base, varies for arm (depends on arm brand mounted)
- **Note**: AGX Lift is a mobile manipulator platform — the arm is typically a third-party arm (UR, Franka, etc.) mounted on AgileX mobile base. The "Lift" refers to the lifting column, not a proprietary arm.
- **For your use**: You likely need the arm-specific SDK + agilex mobile base SDK separately
