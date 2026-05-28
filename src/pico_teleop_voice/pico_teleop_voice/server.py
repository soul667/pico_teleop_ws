"""Voice control WebSocket server: receives audio, returns transcription + commands."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import argparse
from typing import Optional

import msgpack
import numpy as np
import websockets

from pico_teleop_voice.asr import ASREngine
from pico_teleop_voice.intent import IntentParser

logger = logging.getLogger(__name__)

VOICE_PORT = 38271


class VoiceServer:
    def __init__(
        self,
        asr_model: str = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        llm_model: str = "Qwen/Qwen2.5-0.5B-Instruct",
        device: str = "cuda:0",
        port: int = VOICE_PORT,
        robot_ws_url: Optional[str] = None,
    ):
        self._port = port
        self._robot_ws_url = robot_ws_url
        self._asr = ASREngine(model_name=asr_model, device=device)
        self._intent = IntentParser(model_name=llm_model, device=device)
        self._robot_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._clients: set = set()
        self._inference_lock = asyncio.Lock()
        self._robot_lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gpu")

    def load_models(self):
        self._asr.load()
        self._intent.load()
        logger.info("All voice models loaded")

    async def _connect_robot(self):
        if not self._robot_ws_url:
            return
        try:
            self._robot_ws = await websockets.connect(self._robot_ws_url)
            logger.info(f"Connected to robot bridge: {self._robot_ws_url}")
        except Exception as e:
            logger.warning(f"Cannot connect to robot bridge: {e}")

    async def _send_to_robot(self, command: dict):
        if not self._robot_ws:
            await self._connect_robot()
        if self._robot_ws:
            async with self._robot_lock:
                try:
                    await self._robot_ws.send(msgpack.packb(command))
                except websockets.ConnectionClosed:
                    self._robot_ws = None

    async def _handle_client(self, websocket):
        self._clients.add(websocket)
        session = self._asr.create_streaming_session()
        logger.info(f"Voice client connected. Total: {len(self._clients)}")

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    try:
                        msg = msgpack.unpackb(message)
                    except Exception:
                        continue
                    msg_type = msg.get("type")

                    if msg_type == "audio":
                        if "data" not in msg:
                            continue
                        audio = np.frombuffer(
                            bytes(msg["data"]), dtype=np.int16
                        ).astype(np.float32) / 32768.0

                        async with self._inference_lock:
                            partial = await asyncio.get_event_loop().run_in_executor(
                                self._executor, session.feed_audio, audio
                            )
                        if partial:
                            await websocket.send(msgpack.packb({
                                "type": "partial",
                                "text": partial,
                            }))

                    elif msg_type == "end_of_speech":
                        async with self._inference_lock:
                            final_text = await asyncio.get_event_loop().run_in_executor(
                                self._executor, session.finalize
                            )
                        await websocket.send(msgpack.packb({
                            "type": "transcription",
                            "text": final_text,
                        }))

                        if final_text.strip():
                            async with self._inference_lock:
                                command = await asyncio.get_event_loop().run_in_executor(
                                    self._executor, self._intent.parse, final_text
                                )
                            await websocket.send(msgpack.packb({
                                "type": "command",
                                "command": command,
                            }))

                            if command and command.get("action") != "speak":
                                await self._send_to_robot(command)

                    elif msg_type == "cancel":
                        session.reset()

        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            session.reset()
            logger.info(f"Voice client disconnected. Total: {len(self._clients)}")

    async def run(self):
        logger.info(f"Voice server starting on port {self._port}")
        async with websockets.serve(self._handle_client, "0.0.0.0", self._port):
            await asyncio.Future()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--asr-model", default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
    parser.add_argument("--llm-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--port", type=int, default=VOICE_PORT)
    parser.add_argument("--robot-ws-url", default=None)
    args = parser.parse_args()

    server = VoiceServer(
        asr_model=args.asr_model,
        llm_model=args.llm_model,
        device=args.device,
        port=args.port,
        robot_ws_url=args.robot_ws_url,
    )
    server.load_models()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
