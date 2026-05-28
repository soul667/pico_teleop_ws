"""Retarget Node: Maps VR controller poses to robot target EE poses.

Handles:
- Coordinate frame transform (VR frame → robot base frame)
- Workspace scaling (VR space → robot reachable space)
- Clutch mechanism (grip button = enable/disable)
- Origin reset on clutch re-engage
"""

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState

from pico_teleop_msgs.msg import DualArmPose, ButtonEvent, TeleopState


class RetargetNode(Node):
    def __init__(self):
        super().__init__('retarget_node')

        # Parameters
        self.declare_parameter('workspace_scale', 1.0)
        self.declare_parameter('control_frame', 'world')  # 'world' or 'tool'
        self.declare_parameter('arm_config', 'default')

        # State
        self._left_engaged = False
        self._right_engaged = False
        self._left_vr_origin = None
        self._right_vr_origin = None
        self._left_robot_origin = None
        self._right_robot_origin = None

        # Subscribers
        self.create_subscription(
            PoseStamped, '/pico/left_pose', self._on_left_pose, 10)
        self.create_subscription(
            PoseStamped, '/pico/right_pose', self._on_right_pose, 10)
        self.create_subscription(
            ButtonEvent, '/pico/buttons', self._on_button, 10)
        self.create_subscription(
            JointState, '/joint_states', self._on_joint_states, 10)

        # Publishers
        self._target_pub = self.create_publisher(
            DualArmPose, '/teleop/target_poses', 10)
        self._state_pub = self.create_publisher(
            TeleopState, '/teleop/state', 10)

        self._last_joint_states = None
        self._left_gripper = 0.0
        self._right_gripper = 0.0

        self.get_logger().info('RetargetNode initialized')

    def _on_joint_states(self, msg: JointState):
        self._last_joint_states = msg

    def _on_button(self, msg: ButtonEvent):
        """Handle clutch (grip) and gripper (trigger) buttons."""
        if msg.button == 'grip':
            engaged = msg.event == 'pressed'
            if msg.hand == 'left':
                if engaged and not self._left_engaged:
                    # Re-engage: reset origin
                    self._left_vr_origin = None
                self._left_engaged = engaged
            else:
                if engaged and not self._right_engaged:
                    self._right_vr_origin = None
                self._right_engaged = engaged

        elif msg.button == 'trigger':
            # Analog gripper control
            if msg.hand == 'left':
                self._left_gripper = msg.value
            else:
                self._right_gripper = msg.value

    def _on_left_pose(self, msg: PoseStamped):
        if not self._left_engaged:
            return
        target = self._retarget(msg, 'left')
        if target is not None:
            self._publish_targets(left=target)

    def _on_right_pose(self, msg: PoseStamped):
        if not self._right_engaged:
            return
        target = self._retarget(msg, 'right')
        if target is not None:
            self._publish_targets(right=target)

    def _retarget(self, msg: PoseStamped, side: str) -> PoseStamped | None:
        """Map VR pose to robot target pose using relative mapping."""
        scale = self.get_parameter('workspace_scale').value
        pos = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z,
        ])

        # Get/set origin on first frame after clutch engage
        if side == 'left':
            if self._left_vr_origin is None:
                self._left_vr_origin = pos.copy()
                # TODO: get current EE pose as robot origin
                self._left_robot_origin = np.zeros(3)
                return None
            delta = pos - self._left_vr_origin
            robot_origin = self._left_robot_origin
        else:
            if self._right_vr_origin is None:
                self._right_vr_origin = pos.copy()
                self._right_robot_origin = np.zeros(3)
                return None
            delta = pos - self._right_vr_origin
            robot_origin = self._right_robot_origin

        # Apply workspace scaling
        target_pos = robot_origin + delta * scale

        # Build target PoseStamped
        target = PoseStamped()
        target.header.stamp = self.get_clock().now().to_msg()
        target.header.frame_id = 'base_link'
        target.pose.position.x = float(target_pos[0])
        target.pose.position.y = float(target_pos[1])
        target.pose.position.z = float(target_pos[2])
        # Pass through orientation directly (VR → robot EE)
        target.pose.orientation = msg.pose.orientation

        return target

    def _publish_targets(
        self,
        left: PoseStamped | None = None,
        right: PoseStamped | None = None,
    ):
        msg = DualArmPose()
        msg.header.stamp = self.get_clock().now().to_msg()
        if left is not None:
            msg.left_pose = left
        if right is not None:
            msg.right_pose = right
        msg.left_gripper = self._left_gripper
        msg.right_gripper = self._right_gripper
        self._target_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = RetargetNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
