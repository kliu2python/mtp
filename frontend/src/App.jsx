import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import {
  Layout,
  Menu,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  message,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Space,
  Drawer,
  Spin,
  Typography,
  Popconfirm
} from 'antd';
import {
  DashboardOutlined,
  CloudServerOutlined,
  MobileOutlined,
  FileOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  PlusOutlined,
  ReloadOutlined,
  CodeOutlined,
  FileTextOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import axios from 'axios';
import './App.css';

const { Header, Content, Sider } = Layout;

const API_URL = import.meta.env.VITE_API_URL || 'http://10.160.24.60:8000';

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
  const [vmModalOpen, setVmModalOpen] = useState(false);
  const [vmModalMode, setVmModalMode] = useState('create');
  const [savingVm, setSavingVm] = useState(false);
  const [form] = Form.useForm();
  const [editingVm, setEditingVm] = useState(null);
  const [selectedVm, setSelectedVm] = useState(null);
  const [sshModalOpen, setSshModalOpen] = useState(false);
  const [logsDrawerOpen, setLogsDrawerOpen] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [metricsDrawerOpen, setMetricsDrawerOpen] = useState(false);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    fetchVMs();
  }, []);

  const fetchVMs = async () => {
    try {
      setLoading(true);
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

  const deleteVM = async (vmId) => {
    try {
      setDeletingId(vmId);
      await axios.delete(`${API_URL}/api/vms/${vmId}`);
      message.success('VM deleted successfully');
      fetchVMs();
    } catch (error) {
      message.error('Failed to delete VM');
    } finally {
      setDeletingId(null);
    }
  };

  const openCreateModal = () => {
    form.resetFields();
    setEditingVm(null);
    setVmModalMode('create');
    setVmModalOpen(true);
  };

  const openEditModal = (vm) => {
    form.resetFields();
    setEditingVm(vm);
    setVmModalMode('edit');
    form.setFieldsValue({
      name: vm.name,
      platform: vm.platform,
      version: vm.version,
      test_priority: vm.test_priority,
      ip_address: vm.ip_address,
      ssh_username: vm.ssh_username,
      ssh_password: vm.ssh_password,
    });
    setVmModalOpen(true);
  };

  const handleSaveVm = async () => {
    try {
      const values = await form.validateFields();
      setSavingVm(true);
      if (vmModalMode === 'edit' && editingVm) {
        await axios.put(`${API_URL}/api/vms/${editingVm.id}`, values);
        message.success('Virtual machine updated');
      } else {
        await axios.post(`${API_URL}/api/vms`, values);
        message.success('Virtual machine created');
      }
      setVmModalOpen(false);
      setEditingVm(null);
      setVmModalMode('create');
      form.resetFields();
      fetchVMs();
    } catch (error) {
      if (error?.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else if (error?.errorFields) {
        // Validation errors are handled by form
      } else {
        message.error('Failed to save VM');
      }
    } finally {
      setSavingVm(false);
    }
  };

  const openSshModal = (vm) => {
    setSelectedVm(vm);
    setSshModalOpen(true);
  };

  const hasSshDetails = selectedVm?.ip_address && selectedVm?.ssh_username;
  const sshCommand = hasSshDetails
    ? `ssh ${selectedVm.ssh_username}@${selectedVm.ip_address}`
    : 'No SSH connection details available for this VM yet.';

  const handleLaunchSsh = () => {
    if (hasSshDetails) {
      window.open(`ssh://${selectedVm.ssh_username}@${selectedVm.ip_address}`, '_blank');
    }
  };

  const openLogsDrawer = async (vm) => {
    setSelectedVm(vm);
    setLogs([]);
    setLogsDrawerOpen(true);
    setLogsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/vms/${vm.id}/logs`, {
        params: { tail: 200 }
      });
      setLogs(response.data.logs || []);
    } catch (error) {
      message.error('Failed to load VM logs');
    } finally {
      setLogsLoading(false);
    }
  };

  const refreshLogs = async () => {
    if (!selectedVm) return;
    setLogsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/vms/${selectedVm.id}/logs`, {
        params: { tail: 200 }
      });
      setLogs(response.data.logs || []);
    } catch (error) {
      message.error('Failed to refresh logs');
    } finally {
      setLogsLoading(false);
    }
  };

  const openMetricsDrawer = async (vm) => {
    setSelectedVm(vm);
    setMetrics(null);
    setMetricsDrawerOpen(true);
    setMetricsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/vms/${vm.id}/metrics`);
      setMetrics(response.data);
    } catch (error) {
      message.error('Failed to load VM metrics');
    } finally {
      setMetricsLoading(false);
    }
  };

  const refreshMetrics = async () => {
    if (!selectedVm) return;
    setMetricsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/vms/${selectedVm.id}/metrics`);
      setMetrics(response.data);
    } catch (error) {
      message.error('Failed to refresh metrics');
    } finally {
      setMetricsLoading(false);
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
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (value) => value || 'Not set',
    },
    {
      title: 'SSH Username',
      dataIndex: 'ssh_username',
      key: 'ssh_username',
      render: (value) => value || 'Not set',
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
        <Space size="small" wrap>
          {record.status !== 'running' ? (
            <Button type="primary" size="small" onClick={() => startVM(record.id)}>
              Start
            </Button>
          ) : (
            <Button danger size="small" onClick={() => stopVM(record.id)}>
              Stop
            </Button>
          )}
          <Button
            size="small"
            icon={<CodeOutlined />}
            onClick={() => openSshModal(record)}
          >
            SSH
          </Button>
          <Button
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => openLogsDrawer(record)}
          >
            Logs
          </Button>
          <Button
            size="small"
            icon={<BarChartOutlined />}
            onClick={() => openMetricsDrawer(record)}
          >
            Metrics
          </Button>
          <Button
            size="small"
            onClick={() => openEditModal(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Delete VM"
            description="This action cannot be undone."
            onConfirm={() => deleteVM(record.id)}
            okText="Delete"
            okType="danger"
            okButtonProps={{ loading: deletingId === record.id }}
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              loading={deletingId === record.id}
            >
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <h1 style={{ margin: 0 }}>Virtual Machines</h1>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchVMs} loading={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            Add VM
          </Button>
        </Space>
      </div>
      <Table dataSource={vms} columns={columns} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />

      <Modal
        title={vmModalMode === 'edit' ? 'Edit Virtual Machine' : 'Create Virtual Machine'}
        open={vmModalOpen}
        onOk={handleSaveVm}
        onCancel={() => {
          setVmModalOpen(false);
          setEditingVm(null);
          setVmModalMode('create');
          form.resetFields();
        }}
        okText={vmModalMode === 'edit' ? 'Save Changes' : 'Create'}
        confirmLoading={savingVm}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ platform: 'FortiGate', test_priority: 3, ssh_username: 'admin' }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Please enter a name for the VM' }]}
          >
            <Input placeholder="FortiGate QA" />
          </Form.Item>
          <Form.Item
            name="platform"
            label="Platform"
            rules={[{ required: true, message: 'Please select a platform' }]}
          >
            <Select
              options={[
                { label: 'FortiGate', value: 'FortiGate' },
                { label: 'FortiAuthenticator', value: 'FortiAuthenticator' }
              ]}
            />
          </Form.Item>
          <Form.Item
            name="version"
            label="Version"
            rules={[{ required: true, message: 'Please provide the firmware version' }]}
          >
            <Input placeholder="7.2.0" />
          </Form.Item>
          <Form.Item
            name="ip_address"
            label="IP Address"
            rules={[{ required: true, message: 'Please provide the VM IP address' }]}
          >
            <Input placeholder="192.168.1.10" />
          </Form.Item>
          <Form.Item
            name="ssh_username"
            label="SSH Username"
            rules={[{ required: true, message: 'Please provide the SSH username' }]}
          >
            <Input placeholder="admin" />
          </Form.Item>
          <Form.Item
            name="ssh_password"
            label="SSH Password"
            rules={[{ required: true, message: 'Please provide the SSH password' }]}
          >
            <Input.Password placeholder="••••••" />
          </Form.Item>
          <Form.Item
            name="test_priority"
            label="Test Priority"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`SSH Console${selectedVm ? ` - ${selectedVm.name}` : ''}`}
        open={sshModalOpen}
        onOk={() => {
          setSshModalOpen(false);
        }}
        onCancel={() => setSshModalOpen(false)}
        okText="Close"
        footer={[
          <Button key="launch" type="primary" onClick={handleLaunchSsh} disabled={!hasSshDetails}>
            Open SSH Client
          </Button>,
          <Button key="close" onClick={() => setSshModalOpen(false)}>
            Close
          </Button>
        ]}
      >
        {hasSshDetails ? (
          <>
            <Typography.Paragraph copyable>{sshCommand}</Typography.Paragraph>
            {selectedVm?.ssh_password ? (
              <Typography.Paragraph copyable>Password: {selectedVm.ssh_password}</Typography.Paragraph>
            ) : (
              <Typography.Text type="secondary">No password saved for this VM.</Typography.Text>
            )}
          </>
        ) : (
          <Typography.Text type="secondary">{sshCommand}</Typography.Text>
        )}
        <Typography.Text type="secondary">
          Use the command above in your preferred terminal. Opening the SSH client requires an SSH handler configured on your
          device.
        </Typography.Text>
      </Modal>

      <Drawer
        title={`Logs${selectedVm ? ` - ${selectedVm.name}` : ''}`}
        placement="right"
        width={480}
        onClose={() => setLogsDrawerOpen(false)}
        open={logsDrawerOpen}
        extra={
          <Button icon={<ReloadOutlined />} size="small" onClick={refreshLogs} disabled={logsLoading}>
            Refresh
          </Button>
        }
      >
        {logsLoading ? (
          <Spin />
        ) : (
          <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: '60vh', overflow: 'auto' }}>
            {logs && logs.length ? logs.join('\n') : 'No logs available'}
          </pre>
        )}
      </Drawer>

      <Drawer
        title={`Metrics${selectedVm ? ` - ${selectedVm.name}` : ''}`}
        placement="right"
        width={360}
        onClose={() => setMetricsDrawerOpen(false)}
        open={metricsDrawerOpen}
        extra={
          <Button icon={<ReloadOutlined />} size="small" onClick={refreshMetrics} disabled={metricsLoading}>
            Refresh
          </Button>
        }
      >
        {metricsLoading ? (
          <Spin />
        ) : metrics ? (
          <Typography.Paragraph>
            <strong>CPU Usage:</strong> {metrics.cpu_usage ?? metrics.cpu_percent ?? 0}%
            <br />
            <strong>Memory Usage:</strong> {metrics.memory_usage ?? metrics.memory_percent ?? 0}%
            <br />
            <strong>Disk Usage:</strong> {metrics.disk_usage ?? metrics.disk_percent ?? 0}%
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary">No metrics available.</Typography.Text>
        )}
      </Drawer>
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
            {collapsed ? 'MTP' : 'Mobile Test Pilot'}
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
            <h2>Mobile Test Pilot</h2>
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
