"""IK Node: Switchable IK solver (cuRobo / MoveIt2 / TRAC-IK).

Subscribes to target EE poses, solves IK, publishes joint commands.
Solver can be switched at runtime via service call.
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint

from pico_teleop_msgs.msg import DualArmPose
from pico_teleop_msgs.srv import SwitchIKSolver


class IKSolverBase(ABC):
    """Abstract base for all IK solver backends."""

    @abstractmethod
    def initialize(self, urdf_path: str, base_frame: str, ee_frame: str) -> bool:
        ...

    @abstractmethod
    def solve(
        self,
        target_pose: PoseStamped,
        current_joints: np.ndarray,
    ) -> Optional[np.ndarray]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class CuroboIKSolver(IKSolverBase):
    """cuRobo GPU-accelerated IK solver."""

    def initialize(self, urdf_path: str, base_frame: str, ee_frame: str) -> bool:
        try:
            from curobo.types.robot import RobotConfig
            from curobo.wrap.reacher.ik_solver import IKSolver, IKSolverConfig

            robot_cfg = RobotConfig.from_basic(urdf_path, base_frame, ee_frame)
            ik_config = IKSolverConfig.load_from_robot_config(
                robot_cfg,
                num_seeds=32,
                position_threshold=0.005,
                rotation_threshold=0.05,
            )
            self._solver = IKSolver(ik_config)
            return True
        except Exception as e:
            print(f'cuRobo init failed: {e}')
            return False

    def solve(
        self,
        target_pose: PoseStamped,
        current_joints: np.ndarray,
    ) -> Optional[np.ndarray]:
        from curobo.types.math import Pose as CuPose
        import torch

        pos = [
            target_pose.pose.position.x,
            target_pose.pose.position.y,
            target_pose.pose.position.z,
        ]
        quat = [
            target_pose.pose.orientation.w,
            target_pose.pose.orientation.x,
            target_pose.pose.orientation.y,
            target_pose.pose.orientation.z,
        ]

        goal = CuPose(
            position=torch.tensor([pos], dtype=torch.float32).cuda(),
            quaternion=torch.tensor([quat], dtype=torch.float32).cuda(),
        )

        result = self._solver.solve_single(
            goal,
            q_init=torch.tensor([current_joints], dtype=torch.float32).cuda(),
        )

        if result.success[0]:
            return result.solution[0].cpu().numpy().flatten()
        return None

    def name(self) -> str:
        return 'curobo'


class MoveItIKSolver(IKSolverBase):
    """MoveIt2 IK solver via MoveGroup action interface."""

    def initialize(self, urdf_path: str, base_frame: str, ee_frame: str) -> bool:
        self._base_frame = base_frame
        self._ee_frame = ee_frame
        self._initialized = True
        return True

    def solve(
        self,
        target_pose: PoseStamped,
        current_joints: np.ndarray,
    ) -> Optional[np.ndarray]:
        # MoveIt2 IK is called via compute_ik service
        # This is a placeholder — actual implementation uses
        # moveit_msgs/srv/GetPositionIK
        return None

    def name(self) -> str:
        return 'moveit'


class TracIKSolver(IKSolverBase):
    """TRAC-IK solver (CPU, fast, no collision)."""

    def initialize(self, urdf_path: str, base_frame: str, ee_frame: str) -> bool:
        try:
            from trac_ik_python.trac_ik import IK

            self._ik = IK(base_frame, ee_frame, urdf_string=open(urdf_path).read())
            self._n_joints = self._ik.number_of_joints
            return True
        except Exception as e:
            print(f'TRAC-IK init failed: {e}')
            return False

    def solve(
        self,
        target_pose: PoseStamped,
        current_joints: np.ndarray,
    ) -> Optional[np.ndarray]:
        p = target_pose.pose.position
        q = target_pose.pose.orientation
        result = self._ik.get_ik(
            current_joints.tolist(),
            p.x, p.y, p.z,
            q.x, q.y, q.z, q.w,
        )
        if result is not None:
            return np.array(result)
        return None

    def name(self) -> str:
        return 'trac_ik'


SOLVERS = {
    'curobo': CuroboIKSolver,
    'moveit': MoveItIKSolver,
    'trac_ik': TracIKSolver,
}


class IKNode(Node):
    def __init__(self):
        super().__init__('ik_node')

        self.declare_parameter('solver', 'trac_ik')
        self.declare_parameter('urdf_path', '')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('ee_frame_left', 'left_ee_link')
        self.declare_parameter('ee_frame_right', 'right_ee_link')

        self._current_joints = None
        self._solver: Optional[IKSolverBase] = None

        self._init_solver(self.get_parameter('solver').value)

        self.create_subscription(
            DualArmPose, '/teleop/target_poses', self._on_target, 10)
        self.create_subscription(
            JointState, '/joint_states', self._on_joint_states, 10)

        self._joint_cmd_pub = self.create_publisher(
            JointState, '/teleop/joint_commands', 10)

        self.create_service(
            SwitchIKSolver, '/teleop/switch_ik_solver', self._switch_solver_cb)

        self.get_logger().info(
            f'IKNode initialized with solver: {self._solver.name() if self._solver else "none"}')

    def _init_solver(self, solver_name: str) -> bool:
        if solver_name not in SOLVERS:
            self.get_logger().error(f'Unknown solver: {solver_name}')
            return False

        solver = SOLVERS[solver_name]()
        urdf_path = self.get_parameter('urdf_path').value
        base_frame = self.get_parameter('base_frame').value
        ee_frame = self.get_parameter('ee_frame_left').value

        if solver.initialize(urdf_path, base_frame, ee_frame):
            self._solver = solver
            return True
        return False

    def _switch_solver_cb(self, request, response):
        success = self._init_solver(request.solver_name)
        response.success = success
        response.message = (
            f'Switched to {request.solver_name}'
            if success
            else f'Failed to switch to {request.solver_name}'
        )
        return response

    def _on_joint_states(self, msg: JointState):
        self._current_joints = np.array(msg.position)

    def _on_target(self, msg: DualArmPose):
        if self._solver is None or self._current_joints is None:
            return

        joint_cmd = JointState()
        joint_cmd.header.stamp = self.get_clock().now().to_msg()

        result = self._solver.solve(msg.left_pose, self._current_joints)
        if result is not None:
            joint_cmd.position = result.tolist()
            self._joint_cmd_pub.publish(joint_cmd)


def main(args=None):
    rclpy.init(args=args)
    node = IKNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
