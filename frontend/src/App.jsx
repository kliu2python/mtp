import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import axios from 'axios';
import {
  AppstoreOutlined,
  BarChartOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  FileOutlined,
  MobileOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import './App.css';
import Dashboard from './components/Dashboard';
import VMs from './components/VMs';
import Devices from './components/Devices';
import ApkBrowser from './components/ApkBrowser';
import TestTracker from './components/TestTracker';
import Files from './components/Files';
import Settings from './components/Settings';
import { API_URL } from './constants';

const { Content, Sider } = Layout;

function MenuContent({ collapsed, settings }) {
  const location = useLocation();

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Dashboard', path: '/' },
    { key: '/vms', icon: <CloudServerOutlined />, label: 'Virtual Machines', path: '/vms' },
    { key: '/devices', icon: <MobileOutlined />, label: 'Devices', path: '/devices' },
    { key: '/apks', icon: <AppstoreOutlined />, label: 'APK Manager', path: '/apks' },
    { key: '/test-tracker', icon: <BarChartOutlined />, label: 'Test Tracker', path: '/test-tracker' },
    { key: '/files', icon: <FileOutlined />, label: 'Files', path: '/files' },
    { key: '/settings', icon: <SettingOutlined />, label: 'Settings', path: '/settings' },
  ];

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
      <div style={{ padding: collapsed.value ? 12 : 16, borderTop: '1px solid rgba(255, 255, 255, 0.2)', color: 'rgba(255, 255, 255, 0.85)', fontSize: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Integrations</div>
        <div style={{ marginBottom: 4, opacity: 0.9 }}>
          Jenkins: {settings?.jenkins_url ? settings.jenkins_url : 'Not configured'}
        </div>
        <div style={{ opacity: 0.9 }}>
          AI: {settings?.ai_provider ? `${settings.ai_provider}${settings?.ai_model ? ` · ${settings.ai_model}` : ''}` : 'Not configured'}
        </div>
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
              <Route path="/test-tracker" element={<TestTracker />} />
              <Route path="/files" element={<Files />} />
              <Route path="/settings" element={<Settings onSettingsChange={setSettings} initialSettings={settings} />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Router>
  );
}

export default App;
