import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, Popover, Space, Tag, Typography } from 'antd';
import axios from 'axios';
import {
  AppstoreOutlined,
  BugOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  FileOutlined,
  MobileOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import './App.css';
import Dashboard from './components/Dashboard';
import VMs from './components/VMs';
import Devices from './components/Devices';
import ApkBrowser from './components/ApkBrowser';
import Files from './components/Files';
import Settings from './components/Settings';
import Mantis from './components/Mantis';
import PreFlight from './components/PreFlight';
import AcceptableTestDetail from './components/AcceptableTestDetail';
import { API_URL, APP_VERSION, COPYRIGHT_YEAR } from './constants';

const { Content, Footer, Sider } = Layout;

function MenuContent({ collapsed, settings }) {
  const location = useLocation();

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Dashboard', path: '/' },
    { key: '/vms', icon: <CloudServerOutlined />, label: 'Testbed', path: '/vms' },
    { key: '/preflight', icon: <SafetyCertificateOutlined />, label: 'PreFlight', path: '/preflight' },
    { key: '/devices', icon: <MobileOutlined />, label: 'Devices', path: '/devices' },
    { key: '/apks', icon: <AppstoreOutlined />, label: 'APK Manager', path: '/apks' },
    { key: '/files', icon: <FileOutlined />, label: 'Files', path: '/files' },
    { key: '/mantis', icon: <BugOutlined />, label: 'Mantis', path: '/mantis' },
    { key: '/settings', icon: <SettingOutlined />, label: 'Settings', path: '/settings' },
  ];

  const integrations = [];

  if (settings?.jenkins_url) {
    integrations.push({
      key: 'jenkins',
      name: 'Jenkins',
      description: (
        <div>
          <div><strong>URL:</strong> {settings.jenkins_url}</div>
          {settings?.jenkins_user && (
            <div><strong>User:</strong> {settings.jenkins_user}</div>
          )}
        </div>
      ),
    });
  }

  if (settings?.ai_provider) {
    integrations.push({
      key: 'ai',
      name: settings.ai_provider,
      description: (
        <div>
          <div><strong>Provider:</strong> {settings.ai_provider}</div>
          {settings?.ai_model && (
            <div><strong>Model:</strong> {settings.ai_model}</div>
          )}
        </div>
      ),
    });
  }

  return (
    <Sider collapsible collapsed={collapsed.value} onCollapse={collapsed.setter}>
      <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 18, fontWeight: 'bold' }}>
        {collapsed.value ? 'MTP' : 'Mobile Test Pilot'}
      </div>
      <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]}>
        {menuItems.map(item => (
          <Menu.Item key={item.key} icon={item.icon}>
            <Link to={item.path}>{item.label}</Link>
          </Menu.Item>
        ))}
      </Menu>
      <div
        style={{
          padding: collapsed.value ? 12 : 16,
          borderTop: '1px solid rgba(255, 255, 255, 0.2)',
          color: 'rgba(255, 255, 255, 0.85)',
          fontSize: 12,
        }}
      >
        <div
          style={{
            fontWeight: 600,
            marginBottom: collapsed.value ? 0 : 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed.value ? 'center' : 'flex-start',
            gap: 6,
          }}
        >
          {!collapsed.value && <span>Integrations</span>}
          <Tag color="blue" style={{ margin: 0, borderRadius: 12, padding: '0 8px' }}>
            {integrations.length}
          </Tag>
        </div>
        {!collapsed.value && (
          integrations.length === 0 ? (
            <Typography.Text style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
              No integrations configured
            </Typography.Text>
          ) : (
            <Space size={[6, 8]} wrap>
              {integrations.map((integration) => (
                <Popover
                  key={integration.key}
                  content={integration.description}
                  placement="right"
                  overlayInnerStyle={{ minWidth: 200 }}
                >
                  <Tag
                    color="cyan"
                    style={{
                      margin: 0,
                      borderRadius: 16,
                      padding: '4px 10px',
                      cursor: 'pointer',
                      boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
                    }}
                  >
                    {integration.name}
                  </Tag>
                </Popover>
              ))}
            </Space>
          )
        )}
      </div>
    </Sider>
  );
}

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [settings, setSettings] = useState(null);

  const loadSettings = async () => {
    try {
      const { data } = await axios.get(`${API_URL}/api/settings`);
      setSettings(data);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to load settings', error);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <MenuContent collapsed={{ value: collapsed, setter: setCollapsed }} settings={settings} />
        <Layout>
          <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/vms" element={<VMs />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/apks" element={<ApkBrowser />} />
              <Route path="/files" element={<Files />} />
              <Route path="/mantis" element={<Mantis />} />
              <Route path="/preflight" element={<PreFlight jenkinsUrl={settings?.jenkins_url} />} />
              <Route path="/preflight/acceptable/:platform/:id" element={<AcceptableTestDetail />} />
              <Route path="/settings" element={<Settings onSettingsChange={setSettings} initialSettings={settings} />} />
            </Routes>
          </Content>
          <Footer style={{ textAlign: 'center', background: '#fff' }}>
            Mobile Test Pilot v{APP_VERSION} · © {COPYRIGHT_YEAR} Fortinet. All rights reserved.
          </Footer>
        </Layout>
      </Layout>
    </Router>
  );
}

export default App;
