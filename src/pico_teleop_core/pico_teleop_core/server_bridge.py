import asyncio
import threading
import time

import msgpack
import websockets
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_srvs.srv import SetBool


class ServerBridge(Node):
    def __init__(self):
        super().__init__('server_bridge')

        self._joint_cmd_sub = self.create_subscription(
            JointState, '/teleop/joint_commands', self._on_joint_commands, 10)

        self._robot_state_pub = self.create_publisher(
            JointState, '/robot/joint_states', 10)

        self._record_srv = self.create_service(
            SetBool, '/teleop/record', self._on_record_service)

        self._clients: set = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ready = threading.Event()
        self._running = True

        self.get_logger().info('ServerBridge initialized, WS port 38270')

    def _on_joint_commands(self, msg: JointState):
        command = {
            'type': 'command',
            'positions': list(msg.position),
            'gripper': list(msg.effort)[0] if msg.effort else 0.0,
            'timestamp': time.time(),
        }
        self._broadcast(command)

    def _on_record_service(self, request, response):
        if request.data:
            self._broadcast({'type': 'record_start', 'episode_name': ''})
            response.message = 'Recording started'
        else:
            self._broadcast({'type': 'record_stop'})
            response.message = 'Recording stopped'
        response.success = True
        return response

    def _broadcast(self, message: dict):
        if not self._loop_ready.is_set():
            return
        data = msgpack.packb(message)
        asyncio.run_coroutine_threadsafe(self._send_all(data), self._loop)

    async def _send_all(self, data: bytes):
        if not self._clients:
            return
        disconnected = set()
        for ws in self._clients.copy():
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                disconnected.add(ws)
        self._clients -= disconnected

    async def _handle_client(self, websocket):
        self._clients.add(websocket)
        self.get_logger().info(f'Robot connected. Total: {len(self._clients)}')
        try:
            async for raw in websocket:
                try:
                    msg = msgpack.unpackb(raw)
                except Exception as e:
                    self.get_logger().error(f'Failed to unpack message: {e}')
                    continue
                if msg.get('type') == 'state':
                    state = JointState()
                    state.header.stamp = self.get_clock().now().to_msg()
                    state.position = msg.get('joint_positions', [])
                    state.velocity = msg.get('joint_velocities', [])
                    self._robot_state_pub.publish(state)
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            self.get_logger().error(f'Client handler error: {e}')
        finally:
            self._clients.discard(websocket)
            self.get_logger().info(f'Robot disconnected. Total: {len(self._clients)}')

    async def _run_ws_server(self):
        self._loop = asyncio.get_running_loop()
        self._loop_ready.set()
        async with websockets.serve(self._handle_client, '0.0.0.0', 38270):
            while self._running:
                await asyncio.sleep(1.0)


def main(args=None):
    rclpy.init(args=args)
    node = ServerBridge()

    ws_thread = threading.Thread(
        target=lambda: asyncio.run(node._run_ws_server()),
        daemon=True,
    )
    ws_thread.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._running = False
        ws_thread.join(timeout=5.0)
        node.destroy_node()
        rclpy.shutdown()