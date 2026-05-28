"""Isaac Sim driver: communicates via standard ROS2 topics exposed by Isaac Sim."""

from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

from pico_teleop_drivers.base_driver import BaseArmDriver, ArmConfig


class IsaacSimDriver(BaseArmDriver):
    def __init__(self, node: Node, robot_name: str, config: ArmConfig):
        self._node = node
        self._robot_name = robot_name
        self._config = config
        self._connected = False
        self._current_positions: Optional[np.ndarray] = None

        self._joint_state_sub = None
        self._trajectory_pub = None

    def connect(self) -> bool:
        self._joint_state_sub = self._node.create_subscription(
            JointState,
            f'/{self._robot_name}/joint_states',
            self._on_joint_states,
            10,
        )
        self._trajectory_pub = self._node.create_publisher(
            JointTrajectory,
            f'/{self._robot_name}/joint_command',
            10,
        )
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False
        if self._joint_state_sub:
            self._node.destroy_subscription(self._joint_state_sub)
        if self._trajectory_pub:
            self._node.destroy_publisher(self._trajectory_pub)

    def get_config(self) -> ArmConfig:
        return self._config

    def get_joint_positions(self) -> np.ndarray:
        if self._current_positions is None:
            return np.zeros(self._config.dof)
        return self._current_positions

    def get_ee_pose(self) -> np.ndarray:
        # Isaac Sim provides this via TF or dedicated topic
        # Placeholder: return zeros
        return np.zeros(7)

    def send_joint_positions(self, positions: np.ndarray):
        if not self._connected or self._trajectory_pub is None:
            return

        traj = JointTrajectory()
        traj.joint_names = self._config.joint_names

        point = JointTrajectoryPoint()
        point.positions = positions.tolist()
        point.time_from_start = Duration(sec=0, nanosec=50_000_000)
        traj.points = [point]

        self._trajectory_pub.publish(traj)

    def send_joint_trajectory(
        self,
        positions: list[np.ndarray],
        timestamps: list[float],
    ):
        if not self._connected or self._trajectory_pub is None:
            return

        traj = JointTrajectory()
        traj.joint_names = self._config.joint_names

        for pos, t in zip(positions, timestamps):
            point = JointTrajectoryPoint()
            point.positions = pos.tolist()
            sec = int(t)
            nanosec = int((t - sec) * 1e9)
            point.time_from_start = Duration(sec=sec, nanosec=nanosec)
            traj.points.append(point)

        self._trajectory_pub.publish(traj)

    def set_gripper(self, value: float):
        # Isaac Sim gripper control via dedicated topic or joint position
        pass

    def emergency_stop(self):
        if self._current_positions is not None:
            self.send_joint_positions(self._current_positions)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _on_joint_states(self, msg: JointState):
        self._current_positions = np.array(msg.position[:self._config.dof])
