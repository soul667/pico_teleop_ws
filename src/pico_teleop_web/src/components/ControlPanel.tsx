import { Card, Select, Slider, Button, Space, Typography } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import ROSLIB from 'roslib';

const { Text } = Typography;

interface ControlPanelProps {
  ros: ROSLIB.Ros | null;
  connected: boolean;
  xrSupported: boolean;
  xrActive: boolean;
  onStartXR: () => void;
  onStopXR: () => void;
}

const ARM_OPTIONS = [
  { value: 'unitree_g1', label: 'Unitree G1' },
  { value: 'limix_oli', label: 'Limix OLI' },
  { value: 'agx_lift', label: 'AGX Lift' },
  { value: 'hans_dual', label: '大族双臂' },
  { value: 'franka_single', label: 'Franka (单臂)' },
  { value: 'isaacsim', label: 'Isaac Sim' },
];

const IK_OPTIONS = [
  { value: 'trac_ik', label: 'TRAC-IK (CPU)' },
  { value: 'curobo', label: 'cuRobo (GPU)' },
  { value: 'moveit', label: 'MoveIt2' },
];

export function ControlPanel({ ros, connected, xrSupported, xrActive, onStartXR, onStopXR }: ControlPanelProps) {
  const callSwitchIK = (solver: string) => {
    if (!ros) return;
    const service = new ROSLIB.Service({
      ros,
      name: '/teleop/switch_ik_solver',
      serviceType: 'pico_teleop_msgs/srv/SwitchIKSolver',
    });
    service.callService(new ROSLIB.ServiceRequest({ solver_name: solver }), () => {});
  };

  const callSwitchArm = (arm: string) => {
    if (!ros) return;
    const service = new ROSLIB.Service({
      ros,
      name: '/teleop/switch_arm',
      serviceType: 'pico_teleop_msgs/srv/SwitchArm',
    });
    service.callService(new ROSLIB.ServiceRequest({ arm_name: arm }), () => {});
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card title="VR Control" size="small">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text>WebXR Session</Text>
            {xrActive ? (
              <Button icon={<PauseCircleOutlined />} onClick={onStopXR} danger>Stop</Button>
            ) : (
              <Button icon={<PlayCircleOutlined />} onClick={onStartXR} type="primary" disabled={!xrSupported || !connected}>
                Start
              </Button>
            )}
          </div>
        </Space>
      </Card>

      <Card title="Arm Configuration" size="small">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Robot Arm</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              options={ARM_OPTIONS}
              defaultValue="franka_single"
              onChange={callSwitchArm}
              disabled={!connected}
            />
          </div>
          <div>
            <Text type="secondary">IK Solver</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              options={IK_OPTIONS}
              defaultValue="trac_ik"
              onChange={callSwitchIK}
              disabled={!connected}
            />
          </div>
        </Space>
      </Card>

      <Card title="Workspace" size="small">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Scale Factor</Text>
            <Slider min={0.2} max={2.0} step={0.1} defaultValue={1.0} disabled={!connected} />
          </div>
        </Space>
      </Card>
    </Space>
  );
}
