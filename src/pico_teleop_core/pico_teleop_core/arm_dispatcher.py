"""Arm Dispatcher: Routes joint commands to the active arm driver."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

from pico_teleop_msgs.srv import SwitchArm


class ArmDispatcher(Node):
    def __init__(self):
        super().__init__('arm_dispatcher')

        self.declare_parameter('arm_config', 'default')
        self.declare_parameter('control_topic', '/joint_trajectory_controller/joint_trajectory')

        self._trajectory_pub = self.create_publisher(
            JointTrajectory,
            self.get_parameter('control_topic').value,
            10,
        )

        self.create_subscription(
            JointState, '/teleop/joint_commands', self._on_joint_cmd, 10)

        self.create_service(
            SwitchArm, '/teleop/switch_arm', self._switch_arm_cb)

        self._joint_names: list[str] = []
        self._active = True

        self.get_logger().info('ArmDispatcher initialized')

    def _switch_arm_cb(self, request, response):
        self.get_logger().info(f'Switching arm to: {request.arm_name}')
        # TODO: load arm config, update joint names, update control topic
        response.success = True
        response.message = f'Switched to {request.arm_name}'
        return response

    def _on_joint_cmd(self, msg: JointState):
        if not self._active:
            return

        traj = JointTrajectory()
        traj.header.stamp = self.get_clock().now().to_msg()
        traj.joint_names = list(msg.name) if msg.name else self._joint_names

        point = JointTrajectoryPoint()
        point.positions = list(msg.position)
        if msg.velocity:
            point.velocities = list(msg.velocity)
        point.time_from_start = Duration(sec=0, nanosec=50_000_000)  # 50ms

        traj.points = [point]
        self._trajectory_pub.publish(traj)


def main(args=None):
    rclpy.init(args=args)
    node = ArmDispatcher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
