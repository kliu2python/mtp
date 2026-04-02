import React, { useState } from 'react';
import { Card, Spin } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const DeviceHub = () => {
  const [isLoading, setIsLoading] = useState(true);
  const deviceHubUrl = "https://devicehub.qa.fortinet-us.com";

  const handleLoad = () => {
    setIsLoading(false);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    // Force reload the iframe
    const iframe = document.getElementById('devicehub-iframe');
    if (iframe) {
      iframe.src = deviceHubUrl;
    }
  };

  return (
    <div style={{ height: 'calc(100vh - 128px)', display: 'flex', flexDirection: 'column' }}>
      <Card
        title="DeviceHub"
        extra={
          <ReloadOutlined
            onClick={handleRefresh}
            style={{ fontSize: 18, cursor: 'pointer', color: '#1890ff' }}
            title="Refresh DeviceHub"
          />
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, overflow: 'hidden', padding: 0 }}
      >
        <div style={{ position: 'relative', height: '100%' }}>
          {isLoading && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 10
            }}>
              <Spin size="large" tip="Loading DeviceHub..." />
            </div>
          )}
          <iframe
            id="devicehub-iframe"
            src={deviceHubUrl}
            onLoad={handleLoad}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              display: 'block'
            }}
            title="DeviceHub"
            allowFullScreen
          />
        </div>
      </Card>
    </div>
  );
};

export default DeviceHub;
