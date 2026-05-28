import { useRef, useState, useCallback, useEffect } from 'react';
import { encode, decode } from '@msgpack/msgpack';

const VOICE_WS_PORT = 38271;

interface VoiceState {
  listening: boolean;
  processing: boolean;
  partialText: string;
  finalText: string;
  lastCommand: Record<string, unknown> | null;
  error: string | null;
}

export function useVoice(serverHost: string) {
  const [state, setState] = useState<VoiceState>({
    listening: false,
    processing: false,
    partialText: '',
    finalText: '',
    lastCommand: null,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const workletRef = useRef<AudioWorkletNode | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const stopListeningRef = useRef<() => void>(() => {});

  const connect = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      const url = `ws://${serverHost}:${VOICE_WS_PORT}`;
      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        resolve();
      };

      ws.onmessage = (event) => {
        try {
          const msg = decode(new Uint8Array(event.data)) as Record<string, unknown>;
          if (msg.type === 'partial') {
            setState(prev => ({ ...prev, partialText: msg.text as string }));
          } else if (msg.type === 'transcription') {
            setState(prev => ({ ...prev, finalText: msg.text as string, processing: false }));
          } else if (msg.type === 'command') {
            setState(prev => ({ ...prev, lastCommand: msg.command as Record<string, unknown> }));
          }
        } catch {}
      };

      ws.onclose = () => {
        wsRef.current = null;
      };

      ws.onerror = () => {
        setState(prev => ({ ...prev, error: 'Voice server connection failed' }));
        resolve();
      };

      wsRef.current = ws;
    });
  }, [serverHost]);

  const startListening = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      await connect();
    }

    if (contextRef.current) {
      await contextRef.current.close();
      contextRef.current = null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true },
      });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      contextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      await audioContext.audioWorklet.addModule('/audio-processor.js');
      const worklet = new AudioWorkletNode(audioContext, 'audio-processor');
      workletRef.current = worklet;

      worklet.port.onmessage = (event) => {
        const pcmData = event.data as Int16Array;
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const msg = encode({ type: 'audio', data: Array.from(pcmData) });
          wsRef.current.send(msg);
        } else if (wsRef.current?.readyState === WebSocket.CLOSED) {
          stopListeningRef.current();
          setState(prev => ({ ...prev, error: 'WebSocket closed unexpectedly' }));
        }
      };

      source.connect(worklet);
      worklet.connect(audioContext.destination);

      setState(prev => ({ ...prev, listening: true, error: null, partialText: '', finalText: '' }));
    } catch (e) {
      setState(prev => ({ ...prev, error: `Microphone access denied: ${e}` }));
    }
  }, [connect]);

  const stopListening = useCallback(() => {
    if (workletRef.current) {
      workletRef.current.disconnect();
      workletRef.current = null;
    }
    if (contextRef.current) {
      contextRef.current.close();
      contextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const msg = encode({ type: 'end_of_speech' });
      wsRef.current.send(msg);
    }

    setState(prev => ({ ...prev, listening: false, processing: true }));
  }, []);

  stopListeningRef.current = stopListening;

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      contextRef.current?.close();
      streamRef.current?.getTracks().forEach(t => t.stop());
    };
  }, []);

  return { ...state, startListening, stopListening, connect };
}
