import { useEffect, useRef, useState, useCallback } from 'react';
import ROSLIB from 'roslib';

export function useROS(url: string) {
  const rosRef = useRef<ROSLIB.Ros | null>(null);
  const [connected, setConnected] = useState(false);
  const [latency, setLatency] = useState(0);

  useEffect(() => {
    const ros = new ROSLIB.Ros({ url });

    ros.on('connection', () => setConnected(true));
    ros.on('close', () => setConnected(false));
    ros.on('error', () => setConnected(false));

    rosRef.current = ros;

    return () => {
      ros.close();
    };
  }, [url]);

  useEffect(() => {
    if (!connected || !rosRef.current) return;

    let activeTopic: ROSLIB.Topic | null = null;

    const interval = setInterval(() => {
      if (activeTopic) {
        activeTopic.unsubscribe();
      }

      const start = performance.now();
      activeTopic = new ROSLIB.Topic({
        ros: rosRef.current!,
        name: '/rosout',
        messageType: 'rcl_interfaces/msg/Log',
      });
      activeTopic.subscribe(() => {
        setLatency(Math.round(performance.now() - start));
        if (activeTopic) {
          activeTopic.unsubscribe();
          activeTopic = null;
        }
      });
    }, 5000);

    return () => {
      clearInterval(interval);
      if (activeTopic) {
        activeTopic.unsubscribe();
      }
    };
  }, [connected]);

  return { ros: rosRef.current, connected, latency };
}
