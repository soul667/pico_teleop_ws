import asyncio
import argparse
import time

import numpy as np

from pico_teleop_robot.bridge import RobotBridge, RobotState, JointCommand
from pico_teleop_robot.data_recorder import DataRecorder


class RobotNode:
    def __init__(self, args):
        self._bridge = RobotBridge(
            server_url=args.server_url,
            state_hz=args.state_hz,
        )
        self._recorder = DataRecorder(
            save_dir=args.data_dir,
            fps=args.record_fps,
            camera_ids=args.cameras,
        )
        self._bridge.set_record_callbacks(
            on_start=self._recorder.start_episode,
            on_stop=self._recorder.stop_episode,
        )
        self._bridge._on_command = self._on_command

        self._dof = args.dof
        self._current_positions = np.zeros(self._dof)
        self._current_velocities = np.zeros(self._dof)
        self._last_command: JointCommand | None = None

    def _on_command(self, cmd: JointCommand):
        self._last_command = cmd
        # TODO: send to actual robot hardware
        # For now, simulate by updating state directly
        self._current_positions = cmd.positions
        self._update_state()

    def _update_state(self):
        self._bridge.update_state(RobotState(
            joint_positions=self._current_positions,
            joint_velocities=self._current_velocities,
            ee_pose=np.zeros(7),
            gripper_pos=self._last_command.gripper if self._last_command else 0.0,
            timestamp=time.time(),
        ))

        if self._recorder.is_recording and self._last_command is not None:
            self._recorder.record_frame(
                joint_positions=self._current_positions,
                joint_velocities=self._current_velocities,
                action=self._last_command.positions,
                gripper_pos=self._last_command.gripper,
            )

    async def run(self):
        self._recorder.open_cameras()
        try:
            await self._bridge.run()
        finally:
            self._recorder.close_cameras()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="ws://localhost:38270")
    parser.add_argument("--state-hz", type=float, default=100.0)
    parser.add_argument("--record-fps", type=int, default=50)
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--cameras", type=int, nargs="*", default=[])
    parser.add_argument("--dof", type=int, default=7)
    args = parser.parse_args()

    node = RobotNode(args)
    asyncio.run(node.run())


if __name__ == "__main__":
    main()
