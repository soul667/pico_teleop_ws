import { Tag, Space } from 'antd';
import { WifiOutlined, DisconnectOutlined, ApiOutlined } from '@ant-design/icons';

interface StatusBarProps {
  connected: boolean;
  xrActive: boolean;
  latency: number;
}

export function StatusBar({ connected, xrActive, latency }: StatusBarProps) {
  return (
    <Space>
      <Tag
        icon={connected ? <WifiOutlined /> : <DisconnectOutlined />}
        color={connected ? 'success' : 'error'}
      >
        ROS2 {connected ? `(${latency}ms)` : 'Disconnected'}
      </Tag>
      <Tag icon={<ApiOutlined />} color={xrActive ? 'processing' : 'default'}>
        XR {xrActive ? 'Active' : 'Idle'}
      </Tag>
    </Space>
  );
}
