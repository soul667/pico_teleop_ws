"""Records teleoperation episodes in LeRobot dataset format (HuggingFace)."""

import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


class DataRecorder:
    def __init__(self, save_dir: str = "./data", fps: int = 50, camera_ids: list[int] | None = None):
        self._save_dir = Path(save_dir)
        self._fps = fps
        self._camera_ids = camera_ids or []
        self._recording = False
        self._cameras: dict[int, cv2.VideoCapture] = {}
        self._episode_index = self._count_existing_episodes()

        self._camera_threads: dict[int, threading.Thread] = {}
        self._latest_frames: dict[int, Optional[np.ndarray]] = {}
        self._camera_lock = threading.Lock()
        self._stop_camera_threads = False

        self._dataset = None
        self._frame_counter = 0

        self._lerobot_available = False
        self._use_hybrid = False
        self._episode_data: list[dict] = []
        self._current_ep_dir: Optional[Path] = None

    def _count_existing_episodes(self) -> int:
        ep_dir = self._save_dir / "data"
        if not ep_dir.exists():
            return 0
        return len(list(ep_dir.glob("episode_*")))

    def _init_lerobot_dataset(self):
        try:
            from lerobot.datasets import LeRobotDataset
            from lerobot.utils.feature_utils import hw_to_dataset_features
        except ImportError:
            import warnings
            warnings.warn("lerobot not installed, falling back to hybrid recording mode")
            self._use_hybrid = True
            return

        n_cameras = len(self._camera_ids)
        image_shape = (480, 640, 3)
        state_dim = 7
        action_dim = 7
        gripper_dim = 1

        features = hw_to_dataset_features(
            observation={
                "state": {"shape": (state_dim,), "dtype": "float32"},
                "velocity": {"shape": (state_dim,), "dtype": "float32"},
                "gripper_pos": {"shape": (gripper_dim,), "dtype": "float32"},
                "images": {
                    f"camera_{i}": {"shape": image_shape, "dtype": "uint8"} for i in self._camera_ids
                },
            },
            action={"shape": (action_dim,), "dtype": "float32"},
        )

        try:
            self._dataset = LeRobotDataset.create(
                repo_id=str(self._save_dir),
                fps=self._fps,
                features=features,
                robot_type="dual_arm",
                use_videos=True,
                image_writer_threads=4,
            )
            self._lerobot_available = True
        except Exception as e:
            import warnings
            warnings.warn(f"LeRobotDataset.create() failed: {e}, falling back to hybrid mode")
            self._use_hybrid = True

    def open_cameras(self):
        self._stop_camera_threads = False
        if self._dataset is None and not self._use_hybrid:
            self._init_lerobot_dataset()

        for cam_id in self._camera_ids:
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                self._cameras[cam_id] = cap
                self._latest_frames[cam_id] = None
                thread = threading.Thread(target=self._camera_read_loop, args=(cam_id,), daemon=True)
                self._camera_threads[cam_id] = thread
                thread.start()
                print(f"[Recorder] Camera {cam_id} opened (background thread started)")
            else:
                print(f"[Recorder] Failed to open camera {cam_id}")

    def _camera_read_loop(self, cam_id: int):
        cap = self._cameras[cam_id]
        while not self._stop_camera_threads:
            ret, img = cap.read()
            with self._camera_lock:
                self._latest_frames[cam_id] = img if ret else None

    def close_cameras(self):
        self._stop_camera_threads = True
        for thread in self._camera_threads.values():
            thread.join(timeout=2.0)
        self._camera_threads.clear()
        for cap in self._cameras.values():
            cap.release()
        self._cameras.clear()
        self._latest_frames.clear()

    def start_episode(self, episode_name: str = ""):
        if self._recording:
            print("[Recorder] Episode already in progress, ignoring start_episode")
            return

        self._recording = True
        self._frame_counter = 0
        self._episode_data = []

        if self._lerobot_available and self._dataset is not None:
            self._dataset.start_episode()
            print(f"[Recorder] Episode {self._episode_index} started (LeRobotDataset)")
        else:
            self._current_ep_dir = self._save_dir / "data" / f"episode_{self._episode_index:05d}"
            self._current_ep_dir.mkdir(parents=True, exist_ok=True)
            for cam_id in self._camera_ids:
                (self._current_ep_dir / f"camera_{cam_id}").mkdir(exist_ok=True)
            print(f"[Recorder] Episode {self._episode_index} started (hybrid) at {self._current_ep_dir}")

    def stop_episode(self):
        if not self._recording:
            return
        self._recording = False

        if self._episode_index == 0:
            return

        if self._lerobot_available and self._dataset is not None:
            try:
                self._dataset.end_episode()
                print(f"[Recorder] Episode {self._episode_index} saved (LeRobotDataset)")
            except Exception as e:
                print(f"[Recorder] Failed to end episode {self._episode_index}: {e}")
            self._episode_index += 1
        else:
            try:
                self._save_episode_hybrid()
                print(f"[Recorder] Episode {self._episode_index} saved (hybrid)")
            except OSError as e:
                print(f"[Recorder] Failed to save episode {self._episode_index}: {e}")
                if self._current_ep_dir is not None:
                    import shutil
                    shutil.rmtree(self._current_ep_dir, ignore_errors=True)
                print(f"[Recorder] Episode {self._episode_index} discarded due to save failure")
            self._current_ep_dir = None
            self._episode_data.clear()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def record_frame(
        self,
        joint_positions: np.ndarray,
        joint_velocities: np.ndarray,
        action: np.ndarray,
        gripper_pos: float,
    ):
        if not self._recording:
            return

        frame_timestamp = time.time()

        frames = {}
        for cam_id in self._camera_ids:
            with self._camera_lock:
                img = self._latest_frames.get(cam_id)
            if img is not None:
                frames[f"camera_{cam_id}"] = img

        if self._lerobot_available and self._dataset is not None:
            frame_data = {
                "observation.state": joint_positions.copy(),
                "observation.velocity": joint_velocities.copy(),
                "observation.gripper_pos": gripper_pos,
                "action": action.copy(),
            }
            for cam_id in self._camera_ids:
                if f"camera_{cam_id}" in frames:
                    frame_data[f"observation.images.camera_{cam_id}"] = frames[f"camera_{cam_id}"]

            self._dataset.append_frame(frame_data, frame_timestamp)
        else:
            for cam_id in self._camera_ids:
                if f"camera_{cam_id}" in frames:
                    frame_path = self._current_ep_dir / f"camera_{cam_id}" / f"frame_{self._frame_counter:05d}.jpg"
                    cv2.imwrite(str(frame_path), frames[f"camera_{cam_id}"])

            frame = {
                "timestamp": frame_timestamp,
                "observation.state": joint_positions.copy(),
                "observation.velocity": joint_velocities.copy(),
                "action": action.copy(),
                "observation.gripper_pos": gripper_pos,
            }
            self._episode_data.append(frame)

        self._frame_counter += 1

    def _save_episode_hybrid(self):
        import json

        ep_dir = self._current_ep_dir
        if ep_dir is None:
            ep_dir = self._save_dir / "data" / f"episode_{self._episode_index:05d}"

        n_frames = len(self._episode_data)
        timestamps = np.array([f["timestamp"] for f in self._episode_data])
        states = np.array([f["observation.state"] for f in self._episode_data])
        velocities = np.array([f["observation.velocity"] for f in self._episode_data])
        actions = np.array([f["action"] for f in self._episode_data])
        grippers = np.array([f["observation.gripper_pos"] for f in self._episode_data])

        np.save(ep_dir / "state.npy", states)
        np.save(ep_dir / "action.npy", actions)
        np.save(ep_dir / "velocity.npy", velocities)
        np.save(ep_dir / "gripper.npy", grippers)
        np.save(ep_dir / "timestamps.npy", timestamps)

        meta_dir = self._save_dir / "meta"
        meta_dir.mkdir(parents=True, exist_ok=True)

        info_path = meta_dir / "info.json"
        if not info_path.exists():
            info = {
                "fps": self._fps,
                "robot_type": "dual_arm",
                "cameras": [f"camera_{cid}" for cid in self._camera_ids],
            }
            info_path.write_text(json.dumps(info, indent=2))

        episodes_path = meta_dir / "episodes.jsonl"
        episode_entry = {
            "episode_index": self._episode_index,
            "n_frames": n_frames,
            "duration_s": float(timestamps[-1] - timestamps[0]) if n_frames > 1 else 0.0,
        }
        with open(episodes_path, "a") as f:
            f.write(json.dumps(episode_entry) + "\n")

        self._episode_index += 1
