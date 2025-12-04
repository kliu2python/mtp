import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
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

const { Content, Sider } = Layout;

function MenuContent({ collapsed }) {
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
    </Sider>
  );
}

function App() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <MenuContent collapsed={{ value: collapsed, setter: setCollapsed }} />
        <Layout>
          <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/vms" element={<VMs />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/apks" element={<ApkBrowser />} />
              <Route path="/test-tracker" element={<TestTracker />} />
              <Route path="/files" element={<Files />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Router>
  );
}

export default App;
