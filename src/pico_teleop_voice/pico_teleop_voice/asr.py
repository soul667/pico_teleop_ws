"""Fun-ASR-Nano-2512 streaming ASR engine."""

import asyncio
import logging
from typing import AsyncGenerator, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ASREngine:
    def __init__(
        self,
        model_name: str = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        device: str = "cuda:0",
        chunk_ms: int = 600,
    ):
        self._model_name = model_name
        self._device = device
        self._chunk_ms = chunk_ms
        self._model = None
        self._sample_rate = 16000
        self._chunk_samples = int(self._sample_rate * chunk_ms / 1000)

    def load(self):
        from funasr import AutoModel

        logger.info(f"Loading ASR model: {self._model_name}")
        self._model = AutoModel(
            model=self._model_name,
            device=self._device,
            disable_update=True,
        )
        logger.info("ASR model loaded")

    def transcribe_batch(self, audio: np.ndarray) -> str:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        result = self._model.generate(input=audio, batch_size_s=300)
        if result and len(result) > 0:
            return result[0].get("text", "")
        return ""

    def create_streaming_session(self) -> "StreamingSession":
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        return StreamingSession(self._model, self._chunk_samples)


class StreamingSession:
    def __init__(self, model, chunk_samples: int):
        self._model = model
        self._chunk_samples = chunk_samples
        self._cache = {}
        self._buffer = np.array([], dtype=np.float32)
        self._is_final = False

    def feed_audio(self, audio_chunk: np.ndarray) -> str:
        self._buffer = np.concatenate([self._buffer, audio_chunk])

        partial_text = ""
        while len(self._buffer) >= self._chunk_samples:
            chunk = self._buffer[: self._chunk_samples]
            self._buffer = self._buffer[self._chunk_samples:]

            try:
                result = self._model.generate(
                    input=chunk,
                    cache=self._cache,
                    is_final=False,
                    chunk_size=[0, 10, 5],
                )
            except Exception:
                self.reset()
                break

            if result and len(result) > 0:
                text = result[0].get("text", "")
                if text:
                    partial_text += text

        return partial_text

    def finalize(self) -> str:
        if len(self._buffer) == 0:
            return ""

        result = self._model.generate(
            input=self._buffer,
            cache=self._cache,
            is_final=True,
            chunk_size=[0, 10, 5],
        )
        self._buffer = np.array([], dtype=np.float32)
        self._cache = {}

        if result and len(result) > 0:
            return result[0].get("text", "")
        return ""

    def reset(self):
        self._buffer = np.array([], dtype=np.float32)
        self._cache = {}
