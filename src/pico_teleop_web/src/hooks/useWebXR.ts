import { useRef, useState, useCallback, useEffect } from 'react';
import ROSLIB from 'roslib';

interface XRState {
  supported: boolean;
  active: boolean;
  start: () => Promise<void>;
  stop: () => void;
}

export function useWebXR(ros: ROSLIB.Ros | null): XRState {
  const sessionRef = useRef<XRSession | null>(null);
  const refSpaceRef = useRef<XRReferenceSpace | null>(null);
  const [active, setActive] = useState(false);
  const [supported] = useState(() => 'xr' in navigator);

  const leftPoseTopic = useRef<ROSLIB.Topic | null>(null);
  const rightPoseTopic = useRef<ROSLIB.Topic | null>(null);
  const buttonTopic = useRef<ROSLIB.Topic | null>(null);

  const initTopics = useCallback(() => {
    if (!ros) return;

    leftPoseTopic.current = new ROSLIB.Topic({
      ros,
      name: '/pico/left_pose',
      messageType: 'geometry_msgs/PoseStamped',
    });

    rightPoseTopic.current = new ROSLIB.Topic({
      ros,
      name: '/pico/right_pose',
      messageType: 'geometry_msgs/PoseStamped',
    });

    buttonTopic.current = new ROSLIB.Topic({
      ros,
      name: '/pico/buttons',
      messageType: 'pico_teleop_msgs/ButtonEvent',
    });
  }, [ros]);

  const publishPose = (topic: ROSLIB.Topic, position: DOMPointReadOnly, orientation: DOMPointReadOnly) => {
    const now = Date.now();
    topic.publish(new ROSLIB.Message({
      header: {
        stamp: { sec: Math.floor(now / 1000), nanosec: (now % 1000) * 1_000_000 },
        frame_id: 'vr_origin',
      },
      pose: {
        position: { x: position.x, y: position.y, z: position.z },
        orientation: { x: orientation.x, y: orientation.y, z: orientation.z, w: orientation.w },
      },
    }));
  };

  const publishButton = (hand: string, button: string, event: string, value: number) => {
    const now = Date.now();
    buttonTopic.current?.publish(new ROSLIB.Message({
      header: {
        stamp: { sec: Math.floor(now / 1000), nanosec: (now % 1000) * 1_000_000 },
        frame_id: '',
      },
      hand,
      button,
      event,
      value,
      axis_x: 0,
      axis_y: 0,
    }));
  };

  const onXRFrameRef = useRef<(time: number, frame: XRFrame) => void>();

  onXRFrameRef.current = (time: number, frame: XRFrame) => {
    const session = sessionRef.current;
    if (!session) return;

    const refSpace = refSpaceRef.current;
    if (!refSpace) return;

    for (const source of session.inputSources) {
      if (!source.gripSpace) continue;

      const pose = frame.getPose(source.gripSpace, refSpace);
      if (!pose) continue;

      const { position, orientation } = pose.transform;
      const topic = source.handedness === 'left' ? leftPoseTopic.current : rightPoseTopic.current;
      if (topic) {
        publishPose(topic, position, orientation);
      }

      if (source.gamepad) {
        const gp = source.gamepad;
        // buttons[0] = trigger, buttons[1] = grip
        if (gp.buttons[0]) {
          publishButton(source.handedness, 'trigger', 'value_changed', gp.buttons[0].value);
        }
        if (gp.buttons[1]) {
          publishButton(source.handedness, 'grip', gp.buttons[1].pressed ? 'pressed' : 'released', gp.buttons[1].value);
        }
      }
    }

    session.requestAnimationFrame((t, f) => onXRFrameRef.current?.(t, f));
  };

  const onXRFrame = (time: number, frame: XRFrame) => {
    onXRFrameRef.current?.(time, frame);
  };

  const start = useCallback(async () => {
    if (!navigator.xr) return;

    initTopics();

    const session = await navigator.xr.requestSession('immersive-vr', {
      requiredFeatures: ['local-floor'],
    });

    const refSpace = await session.requestReferenceSpace('local-floor');
    refSpaceRef.current = refSpace;

    sessionRef.current = session;
    setActive(true);

    session.addEventListener('end', () => {
      sessionRef.current = null;
      setActive(false);
    });

    session.requestAnimationFrame(onXRFrame);
  }, [initTopics]);

  const stop = useCallback(() => {
    sessionRef.current?.end();
  }, []);

  useEffect(() => {
    return () => {
      sessionRef.current?.end();
    };
  }, []);

  return { supported, active, start, stop };
}
