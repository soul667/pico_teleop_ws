import { useState } from 'react';
import { Layout, ConfigProvider, theme, Divider } from 'antd';
import { Canvas } from '@react-three/fiber';
import { ControlPanel } from './components/ControlPanel';
import { RobotControl } from './components/RobotControl';
import { RobotViewer } from './components/RobotViewer';
import { StatusBar } from './components/StatusBar';
import { XROverlay } from './components/XROverlay';
import { VoiceControl } from './components/VoiceControl';
import { useROS } from './hooks/useROS';
import { useWebXR } from './hooks/useWebXR';

const { Header, Sider, Content } = Layout;

export default function App() {
  const [rosUrl] = useState('ws://localhost:9090');
  const ros = useROS(rosUrl);
  const xr = useWebXR(ros.ros);

  return (
    <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
      <Layout style={{ height: '100vh' }}>
        <Header style={{ padding: '0 16px', display: 'flex', alignItems: 'center', gap: 16 }}>
          <h2 style={{ color: '#fff', margin: 0 }}>PICO Teleop</h2>
          <StatusBar connected={ros.connected} xrActive={xr.active} latency={ros.latency} />
        </Header>
        <Layout>
          <Content style={{ position: 'relative' }}>
            <Canvas>
              <RobotViewer />
            </Canvas>
            {xr.active && <XROverlay />}
          </Content>
          <Sider width={340} style={{ padding: 16, overflow: 'auto' }}>
            <ControlPanel
              ros={ros.ros}
              connected={ros.connected}
              xrSupported={xr.supported}
              xrActive={xr.active}
              onStartXR={xr.start}
              onStopXR={xr.stop}
            />
            <Divider />
            <RobotControl ros={ros.ros} connected={ros.connected} />
            <Divider />
            <VoiceControl />
          </Sider>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
