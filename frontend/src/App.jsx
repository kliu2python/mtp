import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu, Card, Row, Col, Statistic, Table, Tag, Button, message } from 'antd';
import {
  DashboardOutlined,
  CloudServerOutlined,
  MobileOutlined,
  FileOutlined,
  ExperimentOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import axios from 'axios';
import './App.css';

const { Header, Content, Sider } = Layout;

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [vmsRes, devicesRes] = await Promise.all([
        axios.get(`${API_URL}/api/vms/stats/summary`),
        axios.get(`${API_URL}/api/devices/stats/summary`)
      ]);
      setStats({
        vms: vmsRes.data,
        devices: devicesRes.data
      });
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch statistics');
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Dashboard</h1>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total VMs"
              value={stats?.vms?.vms?.total || 0}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Running VMs"
              value={stats?.vms?.vms?.running || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Available Devices"
              value={stats?.devices?.by_status?.available || 0}
              prefix={<MobileOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Test Pass Rate (24h)"
              value={stats?.vms?.tests_24h?.pass_rate || 0}
              suffix="%"
              valueStyle={{ color: stats?.vms?.tests_24h?.pass_rate > 80 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="Platform Distribution">
            {stats?.vms?.vms?.by_platform && (
              <div>
                <p>FortiGate: {stats.vms.vms.by_platform.FortiGate}</p>
                <p>FortiAuthenticator: {stats.vms.vms.by_platform.FortiAuthenticator}</p>
              </div>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Device Distribution">
            {stats?.devices?.by_platform && (
              <div>
                <p>iOS: {stats.devices.by_platform.iOS}</p>
                <p>Android: {stats.devices.by_platform.Android}</p>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

// VMs Component
const VMs = () => {
  const [vms, setVms] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVMs();
  }, []);

  const fetchVMs = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/vms`);
      setVms(response.data.vms);
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch VMs');
      setLoading(false);
    }
  };

  const startVM = async (vmId) => {
    try {
      await axios.post(`${API_URL}/api/vms/${vmId}/start`);
      message.success('VM started successfully');
      fetchVMs();
    } catch (error) {
      message.error('Failed to start VM');
    }
  };

  const stopVM = async (vmId) => {
    try {
      await axios.post(`${API_URL}/api/vms/${vmId}/stop`);
      message.success('VM stopped successfully');
      fetchVMs();
    } catch (error) {
      message.error('Failed to stop VM');
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
    },
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'running' ? 'green' : status === 'stopped' ? 'default' : 'red';
        return <Tag color={color}>{status?.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Pass Rate',
      dataIndex: 'pass_rate',
      key: 'pass_rate',
      render: (rate) => `${rate}%`,
    },
    {
      title: 'Priority',
      dataIndex: 'test_priority',
      key: 'test_priority',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <span>
          {record.status !== 'running' ? (
            <Button type="primary" size="small" onClick={() => startVM(record.id)}>
              Start
            </Button>
          ) : (
            <Button danger size="small" onClick={() => stopVM(record.id)}>
              Stop
            </Button>
          )}
        </span>
      ),
    },
  ];

  return (
    <div>
      <h1>Virtual Machines</h1>
      <Table dataSource={vms} columns={columns} rowKey="id" loading={loading} />
    </div>
  );
};

// Devices Component
const Devices = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/devices`);
      setDevices(response.data.devices);
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch devices');
      setLoading(false);
    }
  };

  const refreshDevices = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_URL}/api/devices/refresh`);
      message.success('Devices refreshed');
      fetchDevices();
    } catch (error) {
      message.error('Failed to refresh devices');
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform) => (
        <Tag color={platform === 'iOS' ? 'blue' : 'green'}>{platform}</Tag>
      ),
    },
    {
      title: 'OS Version',
      dataIndex: 'os_version',
      key: 'os_version',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'available' ? 'green' : status === 'busy' ? 'orange' : 'red';
        return <Tag color={color}>{status?.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Battery',
      dataIndex: 'battery_level',
      key: 'battery_level',
      render: (battery) => `${battery}%`,
    },
    {
      title: 'Type',
      dataIndex: 'device_type',
      key: 'device_type',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1>Test Devices</h1>
        <Button type="primary" onClick={refreshDevices}>
          Refresh Devices
        </Button>
      </div>
      <Table dataSource={devices} columns={columns} rowKey="id" loading={loading} />
    </div>
  );
};

// Files Component
const Files = () => {
  return (
    <div>
      <h1>File Browser</h1>
      <Card>
        <p>File browser functionality - Upload and manage test files</p>
        <Button type="primary">Upload File</Button>
      </Card>
    </div>
  );
};

// Tests Component
const Tests = () => {
  const [coverage, setCoverage] = useState(null);

  useEffect(() => {
    fetchCoverage();
  }, []);

  const fetchCoverage = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/tests/coverage`);
      setCoverage(response.data);
    } catch (error) {
      message.error('Failed to fetch coverage data');
    }
  };

  return (
    <div>
      <h1>Test Management</h1>
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Manual Test Cases"
              value={coverage?.total_manual_cases || 0}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Automated Test Cases"
              value={coverage?.total_auto_cases || 0}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Coverage"
              value={coverage?.coverage_percentage || 0}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      {coverage?.by_platform && (
        <Card title="Coverage by Platform" style={{ marginTop: 24 }}>
          {Object.entries(coverage.by_platform).map(([platform, percent]) => (
            <div key={platform}>
              <strong>{platform}:</strong> {percent}%
            </div>
          ))}
        </Card>
      )}
    </div>
  );
};

// Main App Component
function App() {
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Dashboard', path: '/' },
    { key: '/vms', icon: <CloudServerOutlined />, label: 'Virtual Machines', path: '/vms' },
    { key: '/devices', icon: <MobileOutlined />, label: 'Devices', path: '/devices' },
    { key: '/tests', icon: <ExperimentOutlined />, label: 'Tests', path: '/tests' },
    { key: '/files', icon: <FileOutlined />, label: 'Files', path: '/files' },
  ];

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
          <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 18, fontWeight: 'bold' }}>
            {collapsed ? 'TP' : 'Test Platform'}
          </div>
          <Menu theme="dark" mode="inline" defaultSelectedKeys={['/']}>
            {menuItems.map(item => (
              <Menu.Item key={item.key} icon={item.icon}>
                <Link to={item.path}>{item.label}</Link>
              </Menu.Item>
            ))}
          </Menu>
        </Sider>
        <Layout>
          <Header style={{ background: '#fff', padding: '0 24px' }}>
            <h2>Test Automation Platform</h2>
          </Header>
          <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/vms" element={<VMs />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/tests" element={<Tests />} />
              <Route path="/files" element={<Files />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Router>
  );
}

export default App;
