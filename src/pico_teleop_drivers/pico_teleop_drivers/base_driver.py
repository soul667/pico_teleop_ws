from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ArmConfig:
    name: str
    dof: int
    joint_names: list[str]
    urdf_path: str
    base_frame: str
    ee_frame: str
    has_gripper: bool
    joint_limits_lower: np.ndarray
    joint_limits_upper: np.ndarray
    max_velocity: np.ndarray
    max_acceleration: np.ndarray


class BaseArmDriver(ABC):
    """All arm drivers must implement this interface."""

    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def disconnect(self):
        ...

    @abstractmethod
    def get_config(self) -> ArmConfig:
        ...

    @abstractmethod
    def get_joint_positions(self) -> np.ndarray:
        ...

    @abstractmethod
    def get_ee_pose(self) -> np.ndarray:
        """Returns 7-element array: [x, y, z, qx, qy, qz, qw]."""
        ...

    @abstractmethod
    def send_joint_positions(self, positions: np.ndarray):
        ...

    @abstractmethod
    def send_joint_trajectory(
        self,
        positions: list[np.ndarray],
        timestamps: list[float],
    ):
        ...

    @abstractmethod
    def set_gripper(self, value: float):
        """value: 0.0 = closed, 1.0 = open."""
        ...

    @abstractmethod
    def emergency_stop(self):
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        ...
