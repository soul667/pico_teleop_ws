"""Standalone test for voice control pipeline.

Usage:
  # Test with microphone (requires pyaudio):
  pico-voice-test --mode mic

  # Test with audio file:
  pico-voice-test --mode file --audio-path test.wav

  # Test intent parser only (text input):
  pico-voice-test --mode text

  # Test WebSocket client (connect to running server):
  pico-voice-test --mode ws-client --server-url ws://localhost:38271
"""

import argparse
import asyncio
import json
import logging
import sys
import time

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("voice-test")


def test_intent_only(args):
    from pico_teleop_voice.intent import IntentParser

    parser = IntentParser(model_name=args.llm_model, device=args.device)
    logger.info("Loading intent model...")
    parser.load()
    logger.info("Ready. Type commands (Ctrl+C to exit):\n")

    while True:
        try:
            text = input(">>> ")
            if not text.strip():
                continue
            t0 = time.time()
            result = parser.parse(text)
            elapsed = (time.time() - t0) * 1000
            print(f"  [{elapsed:.0f}ms] {json.dumps(result, ensure_ascii=False, indent=2)}\n")
        except (KeyboardInterrupt, EOFError):
            break


def test_file(args):
    import soundfile as sf
    from pico_teleop_voice.asr import ASREngine
    from pico_teleop_voice.intent import IntentParser

    asr = ASREngine(model_name=args.asr_model, device=args.device)
    intent = IntentParser(model_name=args.llm_model, device=args.device)

    logger.info("Loading models...")
    asr.load()
    intent.load()

    audio, sr = sf.read(args.audio_path)
    if sr != 16000:
        logger.error(f"Expected 16kHz, got {sr}Hz. Please resample.")
        return
    if audio.ndim > 1:
        audio = audio[:, 0]

    logger.info(f"Transcribing {args.audio_path} ({len(audio)/sr:.1f}s)...")
    t0 = time.time()
    text = asr.transcribe_batch(audio.astype(np.float32))
    asr_time = (time.time() - t0) * 1000
    logger.info(f"ASR [{asr_time:.0f}ms]: {text}")

    t0 = time.time()
    command = intent.parse(text)
    intent_time = (time.time() - t0) * 1000
    logger.info(f"Intent [{intent_time:.0f}ms]: {json.dumps(command, ensure_ascii=False)}")


def test_microphone(args):
    try:
        import pyaudio
    except ImportError:
        logger.error("pyaudio not installed. Run: pip install pyaudio")
        return

    from pico_teleop_voice.asr import ASREngine
    from pico_teleop_voice.intent import IntentParser

    asr = ASREngine(model_name=args.asr_model, device=args.device)
    intent = IntentParser(model_name=args.llm_model, device=args.device)

    logger.info("Loading models...")
    asr.load()
    intent.load()

    RATE = 16000
    CHUNK = 4096
    SILENCE_THRESHOLD = 500
    SILENCE_CHUNKS = 15  # ~1s of silence to end

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    logger.info("Listening... (speak, pause 1s to process, Ctrl+C to exit)\n")

    try:
        while True:
            frames = []
            silent_count = 0
            speaking = False

            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                amplitude = np.abs(audio_chunk).mean()

                if amplitude > SILENCE_THRESHOLD:
                    speaking = True
                    silent_count = 0
                    frames.append(audio_chunk)
                elif speaking:
                    silent_count += 1
                    frames.append(audio_chunk)
                    if silent_count >= SILENCE_CHUNKS:
                        break

            if not frames:
                continue

            audio = np.concatenate(frames).astype(np.float32) / 32768.0
            duration = len(audio) / RATE
            logger.info(f"Processing {duration:.1f}s audio...")

            t0 = time.time()
            text = asr.transcribe_batch(audio)
            asr_time = (time.time() - t0) * 1000

            if not text.strip():
                continue

            logger.info(f"ASR [{asr_time:.0f}ms]: {text}")

            t0 = time.time()
            command = intent.parse(text)
            intent_time = (time.time() - t0) * 1000
            logger.info(f"Intent [{intent_time:.0f}ms]: {json.dumps(command, ensure_ascii=False)}")
            print()

    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


async def test_ws_client(args):
    import msgpack
    import websockets

    try:
        import pyaudio
    except ImportError:
        logger.error("pyaudio not installed. Run: pip install pyaudio")
        return

    RATE = 16000
    CHUNK = 4096
    SILENCE_THRESHOLD = 500
    SILENCE_CHUNKS = 15

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    logger.info(f"Connecting to {args.server_url}...")
    async with websockets.connect(args.server_url) as ws:
        logger.info("Connected. Listening... (Ctrl+C to exit)\n")

        async def receive_responses():
            async for raw in ws:
                msg = msgpack.unpackb(raw)
                if msg["type"] == "partial":
                    print(f"  [partial] {msg['text']}", end="\r")
                elif msg["type"] == "transcription":
                    print(f"\n  [final] {msg['text']}")
                elif msg["type"] == "command":
                    print(f"  [command] {json.dumps(msg['command'], ensure_ascii=False)}\n")

        recv_task = asyncio.create_task(receive_responses())

        try:
            while True:
                frames = []
                silent_count = 0
                speaking = False

                while True:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    amplitude = np.abs(audio_chunk).mean()

                    if amplitude > SILENCE_THRESHOLD:
                        speaking = True
                        silent_count = 0
                        frames.append(data)
                        await ws.send(msgpack.packb({"type": "audio", "data": data}))
                    elif speaking:
                        silent_count += 1
                        frames.append(data)
                        await ws.send(msgpack.packb({"type": "audio", "data": data}))
                        if silent_count >= SILENCE_CHUNKS:
                            break

                if frames:
                    await ws.send(msgpack.packb({"type": "end_of_speech"}))
                    await asyncio.sleep(1.0)

        except KeyboardInterrupt:
            pass
        finally:
            recv_task.cancel()
            stream.stop_stream()
            stream.close()
            pa.terminate()


def main():
    parser = argparse.ArgumentParser(description="Voice control standalone test")
    parser.add_argument("--mode", choices=["text", "file", "mic", "ws-client"], default="text")
    parser.add_argument("--asr-model", default="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
    parser.add_argument("--llm-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--audio-path", default="test.wav")
    parser.add_argument("--server-url", default="ws://localhost:38271")
    args = parser.parse_args()

    if args.mode == "text":
        test_intent_only(args)
    elif args.mode == "file":
        test_file(args)
    elif args.mode == "mic":
        test_microphone(args)
    elif args.mode == "ws-client":
        asyncio.run(test_ws_client(args))


if __name__ == "__main__":
    main()
