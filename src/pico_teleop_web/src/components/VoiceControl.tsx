import { useState, useEffect } from 'react';
import { Card, Button, Typography, Space, Tag, Alert } from 'antd';
import { AudioOutlined } from '@ant-design/icons';
import { useVoice } from '../hooks/useVoice';

const { Text, Paragraph } = Typography;

export function VoiceControl() {
  const [serverHost, setServerHost] = useState('localhost');
  
  useEffect(() => {
    setServerHost(window.location.hostname);
  }, []);

  const { 
    listening, 
    processing, 
    partialText, 
    finalText, 
    lastCommand, 
    error, 
    startListening, 
    stopListening,
    connect
  } = useVoice(serverHost);

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <Card title="Voice Control" size="small">
      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
      
      <Space direction="vertical" style={{ width: '100%' }}>
        <Button
          type={listening ? "primary" : "default"}
          danger={listening}
          icon={<AudioOutlined spin={listening} />}
          onMouseDown={startListening}
          onMouseUp={stopListening}
          onMouseLeave={() => { if (listening) stopListening(); }}
          onTouchStart={startListening}
          onTouchEnd={stopListening}
          block
          size="large"
          loading={processing}
        >
          {listening ? "Listening (Release to Stop)..." : processing ? "Processing..." : "Hold to Speak"}
        </Button>

        {(partialText || finalText) && (
          <div style={{ background: '#141414', padding: 8, borderRadius: 4 }}>
            <Text type="secondary">Transcription:</Text>
            <Paragraph style={{ margin: 0, minHeight: 24 }}>
              {partialText || finalText}
            </Paragraph>
          </div>
        )}

        {lastCommand && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">Parsed Command:</Text>
            <pre style={{ 
              background: '#141414', 
              padding: 8, 
              borderRadius: 4,
              fontSize: 12,
              margin: '4px 0 0 0',
              overflowX: 'auto'
            }}>
              {JSON.stringify(lastCommand, null, 2)}
            </pre>
          </div>
        )}
      </Space>
    </Card>
  );
}
