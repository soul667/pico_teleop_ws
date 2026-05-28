"""WebSocket bridge: connects to server, receives joint commands, sends robot state."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import msgpack
import numpy as np
import websockets


@dataclass
class RobotState:
    joint_positions: np.ndarray = field(default_factory=lambda: np.zeros(7))
    joint_velocities: np.ndarray = field(default_factory=lambda: np.zeros(7))
    ee_pose: np.ndarray = field(default_factory=lambda: np.zeros(7))
    gripper_pos: float = 0.0
    timestamp: float = 0.0


@dataclass
class JointCommand:
    positions: np.ndarray
    gripper: float
    timestamp: float


class RobotBridge:
    def __init__(
        self,
        server_url: str = "ws://localhost:38270",
        state_hz: float = 100.0,
        on_command: Optional[Callable[[JointCommand], None]] = None,
    ):
        self._server_url = server_url
        self._state_hz = state_hz
        self._on_command = on_command
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._state = RobotState()
        self._running = False
        self._is_recording = False

    @property
    def connected(self) -> bool:
        return self._connected

    def update_state(self, state: RobotState):
        self._state = state

    async def run(self):
        self._running = True
        while self._running:
            try:
                async with websockets.connect(self._server_url) as ws:
                    self._ws = ws
                    self._connected = True
                    print(f"[Bridge] Connected to {self._server_url}")

                    await asyncio.gather(
                        self._send_state_loop(ws),
                        self._receive_commands(ws),
                    )
            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                self._connected = False
                if self._is_recording:
                    self._is_recording = False
                    if self._on_record_stop:
                        try:
                            self._on_record_stop()
                        except Exception as stop_err:
                            print(f"[Bridge] Error calling _on_record_stop on disconnect: {stop_err}")
                print(f"[Bridge] Disconnected: {e}. Reconnecting in 2s...")
                await asyncio.sleep(2.0)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _send_state_loop(self, ws: websockets.WebSocketClientProtocol):
        interval = 1.0 / self._state_hz
        while self._running:
            msg = msgpack.packb({
                "type": "state",
                "joint_positions": self._state.joint_positions.tolist(),
                "joint_velocities": self._state.joint_velocities.tolist(),
                "ee_pose": self._state.ee_pose.tolist(),
                "gripper_pos": self._state.gripper_pos,
                "timestamp": time.time(),
            })
            await ws.send(msg)
            await asyncio.sleep(interval)

    async def _receive_commands(self, ws: websockets.WebSocketClientProtocol):
        async for raw in ws:
            msg = msgpack.unpackb(raw)
            if msg["type"] == "command":
                cmd = JointCommand(
                    positions=np.array(msg["positions"]),
                    gripper=msg["gripper"],
                    timestamp=msg["timestamp"],
                )
                if self._on_command:
                    self._on_command(cmd)
            elif msg["type"] == "record_start":
                if self._is_recording:
                    print("[Bridge] record_start ignored: already recording")
                    continue
                self._is_recording = True
                if self._on_record_start:
                    self._on_record_start(msg.get("episode_name", ""))
            elif msg["type"] == "record_stop":
                if not self._is_recording:
                    print("[Bridge] record_stop ignored: not recording")
                    continue
                self._is_recording = False
                if self._on_record_stop:
                    self._on_record_stop()

    _on_record_start: Optional[Callable[[str], None]] = None
    _on_record_stop: Optional[Callable[[], None]] = None

    def set_record_callbacks(
        self,
        on_start: Callable[[str], None],
        on_stop: Callable[[], None],
    ):
        self._on_record_start = on_start
        self._on_record_stop = on_stop