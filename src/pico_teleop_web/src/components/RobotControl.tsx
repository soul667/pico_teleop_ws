import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Button, Tag, Space, Typography, Statistic, Row, Col, Alert, Badge } from 'antd';
import { StopOutlined, VideoCameraOutlined, FolderOpenOutlined } from '@ant-design/icons';
import ROSLIB from 'roslib';

const { Text } = Typography;

interface RobotControlProps {
  ros: ROSLIB.Ros | null;
  connected: boolean;
}

interface RobotState {
  robotConnected: boolean;
  controlMode: string;
  jointCount: number;
  recording: boolean;
  episodeCount: number;
  latency: number;
}

export function RobotControl({ ros, connected }: RobotControlProps) {
  const [state, setState] = useState<RobotState>({
    robotConnected: false,
    controlMode: 'idle',
    jointCount: 0,
    recording: false,
    episodeCount: 0,
    latency: 0,
  });

  const [recordingDuration, setRecordingDuration] = useState(0);
  const timerRef = useRef<number | null>(null);
  const connectionTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (!ros || !connected) {
      setState(prev => ({ ...prev, robotConnected: false }));
      return;
    }

    const stateTopic = new ROSLIB.Topic({
      ros,
      name: '/teleop/state',
      messageType: 'pico_teleop_msgs/TeleopState',
    });

    stateTopic.subscribe((msg: any) => {
      setState(prev => ({
        ...prev,
        controlMode: msg.control_mode,
        latency: msg.total_latency || 0,
      }));
    });

    const jointTopic = new ROSLIB.Topic({
      ros,
      name: '/robot/joint_states',
      messageType: 'sensor_msgs/JointState',
    });

    jointTopic.subscribe((msg: any) => {
      setState(prev => ({
        ...prev,
        jointCount: msg.position?.length || 0,
        robotConnected: true,
      }));

      if (connectionTimeoutRef.current) {
        window.clearTimeout(connectionTimeoutRef.current);
      }
      connectionTimeoutRef.current = window.setTimeout(() => {
        setState(prev => ({ ...prev, robotConnected: false }));
      }, 2000);
    });

    return () => {
      stateTopic.unsubscribe();
      jointTopic.unsubscribe();
      if (connectionTimeoutRef.current) {
        window.clearTimeout(connectionTimeoutRef.current);
      }
    };
  }, [ros, connected]);

  const toggleRecording = useCallback(() => {
    if (!ros) return;
    
    const nextRecordingState = !state.recording;
    const service = new ROSLIB.Service({
      ros,
      name: '/teleop/record',
      serviceType: 'std_srvs/srv/SetBool',
    });

    const request = new ROSLIB.ServiceRequest({ data: nextRecordingState });
    
    const handleSuccess = () => {
      setState(prev => {
        const newEpisodeCount = !nextRecordingState ? prev.episodeCount + 1 : prev.episodeCount;
        return { ...prev, recording: nextRecordingState, episodeCount: newEpisodeCount };
      });
      
      if (nextRecordingState) {
        setRecordingDuration(0);
        timerRef.current = window.setInterval(() => {
          setRecordingDuration(prev => prev + 1);
        }, 1000);
      } else {
        if (timerRef.current) {
          window.clearInterval(timerRef.current);
          timerRef.current = null;
        }
      }
    };

    service.callService(
      request,
      (res) => {
        if (res.success) {
          handleSuccess();
        } else {
          console.error("Failed to toggle recording:", res.message);
          handleSuccess();
        }
      },
      (err) => {
        console.error("Service error calling /teleop/record:", err);
        handleSuccess();
      }
    );
  }, [ros, state.recording]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, []);

  const emergencyStop = () => {
    if (!ros) return;
    const topic = new ROSLIB.Topic({
      ros,
      name: '/pico/buttons',
      messageType: 'pico_teleop_msgs/ButtonEvent',
    });
    topic.publish(new ROSLIB.Message({
      header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
      hand: 'right',
      button: 'menu',
      event: 'pressed',
      value: 1.0,
      axis_x: 0,
      axis_y: 0,
    }));
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card title="Robot Status" size="small">
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic
              title="Connection"
              valueRender={() => (
                <Tag color={state.robotConnected ? 'success' : 'error'}>
                  {state.robotConnected ? 'Online' : 'Offline'}
                </Tag>
              )}
            />
          </Col>
          <Col span={12}>
            <Statistic title="Joints" value={state.jointCount} />
          </Col>
          <Col span={12}>
            <Statistic
              title="Mode"
              valueRender={() => (
                <Tag color={state.controlMode === 'teleop' ? 'processing' : 'default'}>
                  {state.controlMode.toUpperCase()}
                </Tag>
              )}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="Latency"
              valueRender={() => (
                <Text style={{ color: state.latency > 150 ? '#ff4d4f' : state.latency > 80 ? '#faad14' : '#52c41a' }}>
                  {state.latency > 0 ? `${state.latency.toFixed(1)} ms` : '--'}
                </Text>
              )}
            />
          </Col>
        </Row>
      </Card>

      <Card title="Recording & Data" size="small">
        <Row gutter={[16, 16]} align="middle">
          <Col span={12}>
            <Statistic title="Episodes Recorded" value={state.episodeCount} />
          </Col>
          <Col span={12}>
            <Statistic 
              title="Current Duration" 
              valueRender={() => (
                <Space>
                  {state.recording && <Badge status="processing" color="red" />}
                  <Text style={{ fontFamily: 'monospace', fontSize: '1.2em', color: state.recording ? '#ff4d4f' : 'inherit' }}>
                    {formatTime(recordingDuration)}
                  </Text>
                </Space>
              )} 
            />
          </Col>
          <Col span={24}>
            <Space style={{ marginTop: 8 }}>
              <FolderOpenOutlined style={{ color: '#8c8c8c' }} />
              <Text type="secondary" style={{ fontSize: '0.85em' }}>~/teleop_data/episodes</Text>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card title="Control" size="small">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Button
            size="large"
            icon={state.recording ? <StopOutlined /> : <VideoCameraOutlined />}
            type={state.recording ? 'default' : 'primary'}
            block
            onClick={toggleRecording}
            disabled={!connected || !state.robotConnected}
            style={state.recording ? { borderColor: '#ff4d4f', color: '#ff4d4f' } : {}}
          >
            {state.recording ? 'Stop Recording' : 'Start Recording'}
          </Button>
          
          <Button
            size="large"
            icon={<StopOutlined />}
            danger
            type="primary"
            block
            onClick={emergencyStop}
            disabled={!connected || !state.robotConnected}
            style={{ height: '60px', fontSize: '1.2em', fontWeight: 'bold' }}
          >
            EMERGENCY STOP
          </Button>
        </Space>
      </Card>

      {!state.robotConnected && connected && (
        <Alert
          message="Robot Offline"
          description="Waiting for /robot/joint_states topic activity. Check robot connection."
          type="warning"
          showIcon
        />
      )}
    </Space>
  );
}
