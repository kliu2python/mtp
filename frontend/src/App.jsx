import React, { useState, useEffect, useRef } from 'react';
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
  Popconfirm,
  Alert
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
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

const { Header, Content, Sider } = Layout;

const API_URL = import.meta.env.VITE_API_URL || 'http://10.160.24.60:8000';
const DEVICE_NODES_API_BASE_URL = 'http://10.160.13.118:8090';

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
  const [sshConnecting, setSshConnecting] = useState(false);
  const [sshError, setSshError] = useState(null);
  const sshTerminalRef = useRef(null);
  const sshTerminalInstanceRef = useRef(null);
  const sshFitAddonRef = useRef(null);
  const sshSocketRef = useRef(null);

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
    setSshError(null);
    setSshConnecting(false);
    setSshModalOpen(true);
  };

  const hasSshDetails = selectedVm?.ip_address && selectedVm?.ssh_username;
  const sshCommand = hasSshDetails
    ? `ssh ${selectedVm.ssh_username}@${selectedVm.ip_address}`
    : 'No SSH connection details available for this VM yet.';

  const buildSshWebSocketUrl = (vmId) => {
    try {
      const apiUrl = new URL(API_URL);
      const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      const basePath = apiUrl.pathname.replace(/\/$/, '');
      return `${protocol}//${apiUrl.host}${basePath}/api/vms/${vmId}/ssh`;
    } catch (error) {
      const isSecure = window.location.protocol === 'https:';
      return `${isSecure ? 'wss:' : 'ws:'}//${window.location.host}/api/vms/${vmId}/ssh`;
    }
  };

  const closeSshModal = () => {
    setSshModalOpen(false);
    setSshConnecting(false);
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const closeActiveSocket = () => {
      if (sshSocketRef.current) {
        const state = sshSocketRef.current.readyState;
        if (state === 0 || state === 1) {
          sshSocketRef.current.close();
        }
        sshSocketRef.current = null;
      }
    };

    if (!sshModalOpen) {
      setSshConnecting(false);
      setSshError(null);
      closeActiveSocket();
      if (sshTerminalInstanceRef.current) {
        sshTerminalInstanceRef.current.dispose();
        sshTerminalInstanceRef.current = null;
      }
      sshFitAddonRef.current = null;
      if (sshTerminalRef.current) {
        sshTerminalRef.current.innerHTML = '';
      }
      return;
    }

    if (!selectedVm || !hasSshDetails) {
      return;
    }

    setSshError(null);
    setSshConnecting(true);

    const terminal = new Terminal({
      cursorBlink: true,
      convertEol: true,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14,
      theme: {
        background: '#1f1f1f',
      },
    });
    sshTerminalInstanceRef.current = terminal;

    const fitAddon = new FitAddon();
    sshFitAddonRef.current = fitAddon;
    terminal.loadAddon(fitAddon);

    const container = sshTerminalRef.current;
    if (container) {
      container.innerHTML = '';
      terminal.open(container);
      requestAnimationFrame(() => {
        try {
          fitAddon.fit();
        } catch (error) {
          // Ignore fit errors caused by hidden container transitions
        }
      });
    }

    const handleResize = () => {
      if (sshFitAddonRef.current) {
        try {
          sshFitAddonRef.current.fit();
        } catch (error) {
          // ignore fit errors
        }
      }
    };

    window.addEventListener('resize', handleResize);

    const socket = new WebSocket(buildSshWebSocketUrl(selectedVm.id));
    sshSocketRef.current = socket;
    const textDecoder = typeof TextDecoder !== 'undefined' ? new TextDecoder() : null;

    const dataDisposable = terminal.onData((data) => {
      if (sshSocketRef.current && sshSocketRef.current.readyState === WebSocket.OPEN) {
        sshSocketRef.current.send(data);
      }
    });

    socket.onopen = () => {
      setSshConnecting(false);
      handleResize();
    };

    socket.onmessage = (event) => {
      if (typeof event.data === 'string') {
        terminal.write(event.data);
      } else if (event.data instanceof ArrayBuffer) {
        if (textDecoder) {
          terminal.write(textDecoder.decode(event.data));
        } else {
          const bytes = new Uint8Array(event.data);
          let text = '';
          for (let i = 0; i < bytes.length; i += 1024) {
            const chunk = bytes.subarray(i, i + 1024);
            text += String.fromCharCode(...chunk);
          }
          terminal.write(text);
        }
      }
    };

    socket.onerror = () => {
      setSshConnecting(false);
      setSshError('Failed to establish SSH connection. Please verify the VM credentials and network access.');
      closeActiveSocket();
    };

    socket.onclose = (event) => {
      setSshConnecting(false);
      if (event.code !== 1000) {
        setSshError(event.reason || 'SSH session closed unexpectedly.');
      }
      if (terminal) {
        const reasonText = event.reason ? ` (${event.reason})` : '';
        terminal.write(`\r\nConnection closed [code ${event.code}]${reasonText}.\r\n`);
      }
      if (sshSocketRef.current === socket) {
        sshSocketRef.current = null;
      }
    };

    return () => {
      dataDisposable.dispose();
      window.removeEventListener('resize', handleResize);
      closeActiveSocket();
      if (sshTerminalInstanceRef.current) {
        sshTerminalInstanceRef.current.dispose();
        sshTerminalInstanceRef.current = null;
      }
      sshFitAddonRef.current = null;
      if (sshTerminalRef.current) {
        sshTerminalRef.current.innerHTML = '';
      }
    };
  }, [sshModalOpen, selectedVm, hasSshDetails]);

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
        onCancel={closeSshModal}
        footer={[<Button key="close" onClick={closeSshModal}>Close</Button>]}
        width={820}
        destroyOnClose={false}
        maskClosable={false}
      >
        {hasSshDetails ? (
          <>
            {sshError && (
              <Alert type="error" message={sshError} showIcon style={{ marginBottom: 16 }} />
            )}
            {selectedVm?.ssh_password ? (
              <Typography.Paragraph copyable>
                Password: {selectedVm.ssh_password}
              </Typography.Paragraph>
            ) : (
              <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                No password saved for this VM. Ensure key-based access is configured if required.
              </Typography.Text>
            )}
            <div className="ssh-terminal-wrapper">
              <div ref={sshTerminalRef} className="ssh-terminal" />
              {sshConnecting && (
                <div className="ssh-terminal-overlay">
                  <Space direction="vertical" align="center">
                    <Spin size="large" />
                    <Typography.Text style={{ color: '#fff' }}>Connecting…</Typography.Text>
                  </Space>
                </div>
              )}
            </div>
            <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
              This console is powered by an in-browser SSH client. Closing the modal will terminate the SSH session.
            </Typography.Paragraph>
          </>
        ) : (
          <>
            <Typography.Paragraph copyable>{sshCommand}</Typography.Paragraph>
            <Typography.Text type="secondary">
              Provide SSH credentials for this VM to enable the embedded console.
            </Typography.Text>
          </>
        )}
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
  const [summary, setSummary] = useState({ total: 0, available: 0, busy: 0 });

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      const [nodesResponse, availableResponse] = await Promise.all([
        axios.get(`${DEVICE_NODES_API_BASE_URL}/nodes`),
        axios.get(`${DEVICE_NODES_API_BASE_URL}/nodes/available`)
      ]);

      const nodesData = nodesResponse.data || {};
      const nodes = Object.values(nodesData);

      const availableRaw = availableResponse.data;
      let availableSet = new Set();

      if (Array.isArray(availableRaw)) {
        availableSet = new Set(availableRaw.map((item) => (typeof item === 'string' ? item : item?.id)));
      } else if (availableRaw) {
        if (Array.isArray(availableRaw.available)) {
          availableSet = new Set(
            availableRaw.available.map((item) => (typeof item === 'string' ? item : item?.id))
          );
        } else {
          availableSet = new Set(Object.keys(availableRaw));
        }
      }

      const normalizedDevices = nodes.map((node) => {
        const nodeId = node?.id || node?.deviceName || node?.name;
        const isAvailable = nodeId ? availableSet.has(nodeId) : false;
        let derivedStatus = 'unknown';
        if (isAvailable) {
          derivedStatus = 'available';
        } else if (node?.status) {
          derivedStatus = node.status === 'online' ? 'available' : 'busy';
        } else if (node?.active_sessions > 0) {
          derivedStatus = 'busy';
        }

        return {
          id: nodeId,
          name: node?.deviceName || nodeId,
          platform: node?.platform || 'Unknown',
          os_version: node?.platform_version || 'Unknown',
          status: derivedStatus,
          type: node?.type || 'Unknown',
          host: node?.host,
          port: node?.port,
        };
      });

      const availableCount = normalizedDevices.filter((device) => device.status === 'available').length;
      const busyCount = normalizedDevices.filter((device) => device.status === 'busy').length;
      const totalCount = normalizedDevices.length;

      setSummary({
        total: totalCount,
        available: availableCount,
        busy: busyCount,
      });
      setDevices(normalizedDevices);
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch devices');
      setLoading(false);
    }
  };

  const refreshDevices = async () => {
    try {
      setLoading(true);
      await fetchDevices();
      message.success('Devices refreshed');
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
      render: (platform) => {
        const label = platform || 'Unknown';
        const color = label === 'iOS' ? 'blue' : label === 'Android' ? 'green' : undefined;
        return <Tag color={color}>{label}</Tag>;
      },
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
        const color = status === 'available' ? 'green' : status === 'busy' ? 'orange' : undefined;
        return <Tag color={color}>{status ? status.toUpperCase() : 'UNKNOWN'}</Tag>;
      },
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (value) => value || 'Unknown',
    },
    {
      title: 'Host',
      dataIndex: 'host',
      key: 'host',
      render: (value) => value || 'N/A',
    },
    {
      title: 'Port',
      dataIndex: 'port',
      key: 'port',
      render: (value) => value || 'N/A',
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic title="Total Nodes" value={summary.total} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="Available Nodes" value={summary.available} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="Busy Nodes" value={summary.busy} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
      </Row>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1>Device Nodes</h1>
        <Button type="primary" onClick={refreshDevices}>
          Refresh Nodes
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
