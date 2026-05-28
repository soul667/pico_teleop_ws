import { Tag } from 'antd';

export function XROverlay() {
  return (
    <div style={{
      position: 'absolute',
      top: 16,
      left: 16,
      zIndex: 10,
    }}>
      <Tag color="green">VR Mode Active - Controllers Streaming</Tag>
    </div>
  );
}
