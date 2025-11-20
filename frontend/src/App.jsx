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
  Alert,
  Upload,
  Image,
  Tooltip,
  Progress,
  Empty
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
  DeleteOutlined,
  ClusterOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  UploadOutlined,
  DownloadOutlined,
  EditOutlined,
  QrcodeOutlined,
  EyeOutlined,
  MonitorOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import axios from 'axios';
import './App.css';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import WorkerDashboard from './components/WorkerDashboard';
import ApkBrowser from './components/ApkBrowser';

const { Content, Sider } = Layout;

const API_URL = import.meta.env.VITE_API_URL || '';
// Use backend proxy to avoid mixed content errors
const DEVICE_NODES_API_BASE_URL = `${API_URL}/api/device/nodes/proxy`;

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

// Jenkins Nodes Component
const JenkinsNodes = () => {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nodeModalOpen, setNodeModalOpen] = useState(false);
  const [nodeModalMode, setNodeModalMode] = useState('create');
  const [savingNode, setSavingNode] = useState(false);
  const [form] = Form.useForm();
  const [editingNode, setEditingNode] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState(null);
  const [poolStats, setPoolStats] = useState(null);

  useEffect(() => {
    fetchNodes();
    fetchPoolStats();
  }, []);

  const fetchNodes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/jenkins/nodes`);
      setNodes(response.data.nodes);
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch Jenkins nodes');
      setLoading(false);
    }
  };

  const fetchPoolStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/jenkins/nodes/pool/stats`);
      setPoolStats(response.data);
    } catch (error) {
      console.error('Failed to fetch pool stats:', error);
    }
  };

  const testConnection = async () => {
    try {
      const values = await form.validateFields(['host', 'port', 'username', 'password', 'ssh_key']);
      setTestingConnection(true);
      setConnectionTestResult(null);

      const response = await axios.post(`${API_URL}/api/jenkins/nodes/test-connection`, {
        host: values.host,
        port: values.port || 22,
        username: values.username,
        password: values.password,
        ssh_key: values.ssh_key
      });

      setConnectionTestResult({
        success: true,
        message: response.data.message,
        latency: response.data.latency,
        cpu_usage: response.data.cpu_usage,
        memory_usage: response.data.memory_usage,
        disk_usage: response.data.disk_usage
      });
      message.success('Connection test successful!');
    } catch (error) {
      const errorMsg = error?.response?.data?.detail || 'Connection test failed';
      setConnectionTestResult({
        success: false,
        message: errorMsg
      });
      message.error(errorMsg);
    } finally {
      setTestingConnection(false);
    }
  };

  const pingNode = async (nodeId) => {
    try {
      const response = await axios.post(`${API_URL}/api/jenkins/nodes/${nodeId}/ping`);
      message.success(`Ping successful: ${response.data.latency}s`);
      fetchNodes();
      fetchPoolStats();
    } catch (error) {
      message.error('Failed to ping node');
    }
  };

  const enableNode = async (nodeId) => {
    try {
      await axios.post(`${API_URL}/api/jenkins/nodes/${nodeId}/enable`);
      message.success('Node enabled');
      fetchNodes();
      fetchPoolStats();
    } catch (error) {
      message.error('Failed to enable node');
    }
  };

  const disableNode = async (nodeId) => {
    try {
      await axios.post(`${API_URL}/api/jenkins/nodes/${nodeId}/disable`);
      message.success('Node disabled');
      fetchNodes();
      fetchPoolStats();
    } catch (error) {
      message.error('Failed to disable node');
    }
  };

  const deleteNode = async (nodeId) => {
    try {
      setDeletingId(nodeId);
      await axios.delete(`${API_URL}/api/jenkins/nodes/${nodeId}`);
      message.success('Node deleted successfully');
      fetchNodes();
      fetchPoolStats();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Failed to delete node');
    } finally {
      setDeletingId(null);
    }
  };

  const healthCheckAll = async () => {
    try {
      message.loading('Running health check on all nodes...');
      await axios.post(`${API_URL}/api/jenkins/nodes/pool/health-check`);
      message.success('Health check completed');
      fetchNodes();
      fetchPoolStats();
    } catch (error) {
      message.error('Failed to run health check');
    }
  };

  const openCreateModal = () => {
    form.resetFields();
    setEditingNode(null);
    setNodeModalMode('create');
    setConnectionTestResult(null);
    setNodeModalOpen(true);
  };

  const openEditModal = (node) => {
    form.resetFields();
    setEditingNode(node);
    setNodeModalMode('edit');
    setConnectionTestResult(null);
    form.setFieldsValue({
      name: node.name,
      description: node.description,
      host: node.host,
      port: node.port,
      username: node.username,
      password: node.password,
      ssh_key: node.ssh_key,
      max_executors: node.max_executors,
      labels: node.labels,
      tags: node.tags
    });
    setNodeModalOpen(true);
  };

  const handleSaveNode = async () => {
    try {
      const values = await form.validateFields();
      setSavingNode(true);

      if (nodeModalMode === 'edit' && editingNode) {
        await axios.put(`${API_URL}/api/jenkins/nodes/${editingNode.id}`, values);
        message.success('Jenkins node updated');
      } else {
        await axios.post(`${API_URL}/api/jenkins/nodes`, values);
        message.success('Jenkins node created');
      }

      setNodeModalOpen(false);
      setEditingNode(null);
      setNodeModalMode('create');
      form.resetFields();
      setConnectionTestResult(null);
      fetchNodes();
      fetchPoolStats();
    } catch (error) {
      if (error?.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else if (error?.errorFields) {
        // Validation errors are handled by form
      } else {
        message.error('Failed to save node');
      }
    } finally {
      setSavingNode(false);
    }
  };

  const getStatusTag = (status) => {
    const statusConfig = {
      online: { color: 'success', icon: <CheckCircleOutlined /> },
      busy: { color: 'processing', icon: <SyncOutlined spin /> },
      offline: { color: 'default', icon: <CloseCircleOutlined /> },
      error: { color: 'error', icon: <CloseCircleOutlined /> },
      testing: { color: 'warning', icon: <SyncOutlined spin /> }
    };
    const config = statusConfig[status] || statusConfig.offline;
    return <Tag color={config.color} icon={config.icon}>{status.toUpperCase()}</Tag>;
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      fixed: 'left'
    },
    {
      title: 'Host',
      dataIndex: 'host',
      key: 'host',
      render: (host, record) => `${host}:${record.port}`
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status)
    },
    {
      title: 'Executors',
      key: 'executors',
      render: (_, record) => `${record.current_executors}/${record.max_executors}`
    },
    {
      title: 'Resources',
      key: 'resources',
      render: (_, record) => (
        <div>
          <div>CPU: {record.cpu_usage}%</div>
          <div>Mem: {record.memory_usage}%</div>
          <div>Disk: {record.disk_usage}%</div>
        </div>
      )
    },
    {
      title: 'Tests',
      key: 'tests',
      render: (_, record) => (
        <div>
          <div>Total: {record.total_tests_executed}</div>
          <div>Pass Rate: {record.pass_rate}%</div>
        </div>
      )
    },
    {
      title: 'Labels',
      dataIndex: 'labels',
      key: 'labels',
      render: (labels) => (
        <>
          {labels?.map(label => (
            <Tag key={label}>{label}</Tag>
          ))}
        </>
      )
    },
    {
      title: 'Enabled',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled) => enabled ? <Tag color="success">Yes</Tag> : <Tag color="default">No</Tag>
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<SyncOutlined />}
            onClick={() => pingNode(record.id)}
            title="Ping node"
          />
          {record.enabled ? (
            <Button
              size="small"
              onClick={() => disableNode(record.id)}
              title="Disable node"
            >
              Disable
            </Button>
          ) : (
            <Button
              size="small"
              type="primary"
              onClick={() => enableNode(record.id)}
              title="Enable node"
            >
              Enable
            </Button>
          )}
          <Button
            size="small"
            onClick={() => openEditModal(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this node?"
            onConfirm={() => deleteNode(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              loading={deletingId === record.id}
            />
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1>Jenkins Slave Nodes</h1>
        <Space>
          <Button
            type="default"
            icon={<SyncOutlined />}
            onClick={healthCheckAll}
          >
            Health Check All
          </Button>
          <Button
            type="default"
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchNodes();
              fetchPoolStats();
            }}
          >
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={openCreateModal}
          >
            Add Node
          </Button>
        </Space>
      </div>

      {poolStats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Card>
              <Statistic
                title="Total Nodes"
                value={poolStats.total_nodes}
                prefix={<ClusterOutlined />}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="Online"
                value={poolStats.online_nodes}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="Busy"
                value={poolStats.busy_nodes}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="Available Executors"
                value={poolStats.available_executors}
                suffix={`/ ${poolStats.total_executors}`}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="Tests Executed"
                value={poolStats.total_tests_executed}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card>
              <Statistic
                title="Pass Rate"
                value={poolStats.pass_rate}
                suffix="%"
                valueStyle={{ color: poolStats.pass_rate >= 80 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Table
        columns={columns}
        dataSource={nodes}
        loading={loading}
        rowKey="id"
        scroll={{ x: 1200 }}
      />

      <Modal
        title={nodeModalMode === 'create' ? 'Add Jenkins Slave Node' : 'Edit Jenkins Slave Node'}
        open={nodeModalOpen}
        onOk={handleSaveNode}
        onCancel={() => {
          setNodeModalOpen(false);
          setConnectionTestResult(null);
        }}
        confirmLoading={savingNode}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter node name' }]}
          >
            <Input placeholder="e.g., jenkins-slave-01" />
          </Form.Item>

          <Form.Item label="Description" name="description">
            <Input.TextArea placeholder="Optional description" rows={2} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                label="Host"
                name="host"
                rules={[{ required: true, message: 'Please enter host' }]}
              >
                <Input placeholder="e.g., 192.168.1.100" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Port"
                name="port"
                initialValue={22}
                rules={[{ required: true, message: 'Please enter port' }]}
              >
                <InputNumber placeholder="22" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Username"
            name="username"
            rules={[{ required: true, message: 'Please enter username' }]}
          >
            <Input placeholder="SSH username" />
          </Form.Item>

          <Form.Item label="Password" name="password">
            <Input.Password placeholder="SSH password (optional if using SSH key)" />
          </Form.Item>

          <Form.Item label="SSH Key Path" name="ssh_key">
            <Input placeholder="/path/to/private/key (optional if using password)" />
          </Form.Item>

          <Form.Item
            label="Max Executors"
            name="max_executors"
            initialValue={2}
            rules={[{ required: true, message: 'Please enter max executors' }]}
          >
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="Labels" name="labels">
            <Select
              mode="tags"
              placeholder="e.g., android, ios, linux"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label="Tags" name="tags">
            <Select
              mode="tags"
              placeholder="Additional tags"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="default"
              onClick={testConnection}
              loading={testingConnection}
              icon={<SyncOutlined />}
              block
            >
              Test Connection
            </Button>
          </Form.Item>

          {connectionTestResult && (
            <Alert
              message={connectionTestResult.success ? 'Connection Successful' : 'Connection Failed'}
              description={
                <div>
                  <div>{connectionTestResult.message}</div>
                  {connectionTestResult.success && (
                    <div style={{ marginTop: 8 }}>
                      <div>Latency: {connectionTestResult.latency}s</div>
                      <div>CPU Usage: {connectionTestResult.cpu_usage}%</div>
                      <div>Memory Usage: {connectionTestResult.memory_usage}%</div>
                      <div>Disk Usage: {connectionTestResult.disk_usage}%</div>
                    </div>
                  )}
                </div>
              }
              type={connectionTestResult.success ? 'success' : 'error'}
              showIcon
              style={{ marginTop: 8 }}
            />
          )}
        </Form>
      </Modal>
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

  // Auto Test states
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testForm] = Form.useForm();
  const [selectedTestVm, setSelectedTestVm] = useState(null);
  const [startingTest, setStartingTest] = useState(false);
  const [runningTests, setRunningTests] = useState({});
  const [testPollingInterval, setTestPollingInterval] = useState(null);

  // Run Previous states
  const [runPreviousModalOpen, setRunPreviousModalOpen] = useState(false);
  const [runPreviousForm] = Form.useForm();
  const [previousTestConfig, setPreviousTestConfig] = useState(null);
  const [loadingPreviousConfig, setLoadingPreviousConfig] = useState(false);

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

  const openTestModal = (vm) => {
    setSelectedTestVm(vm);
    testForm.resetFields();
    // Set default values based on VM
    testForm.setFieldsValue({
      platform: vm.platform === 'FortiGate' ? 'ios' : 'android',
      execution_method: 'docker',
      test_suite: 'FortiToken_Mobile',
      test_markers: 'smoke',
      timeout: 3600,
      docker_registry: 'docker.io',
      docker_image: 'pytest-automation',
      docker_tag: 'latest'
    });
    setTestModalOpen(true);
  };

  const runAutoTest = async () => {
    try {
      const values = await testForm.validateFields();
      setStartingTest(true);

      const testConfig = {
        name: `Auto Test - ${selectedTestVm.name}`,
        vm_id: selectedTestVm.id,
        device_ids: [],
        test_scripts: [],
        environment: {
          vm_ip: selectedTestVm.ip_address,
          vm_username: selectedTestVm.ssh_username,
          vm_password: selectedTestVm.ssh_password,
          platform: values.platform,
          execution_method: values.execution_method,
          test_suite: values.test_suite,
          test_markers: values.test_markers,
          docker_registry: values.docker_registry,
          docker_image: values.docker_image,
          docker_tag: values.docker_tag,
        },
        timeout: values.timeout
      };

      const response = await axios.post(`${API_URL}/api/tests/execute`, testConfig);

      if (response.data.task_id) {
        message.success(`Test queued successfully! Task ID: ${response.data.task_id}`);

        // Store the running test
        setRunningTests(prev => ({
          ...prev,
          [response.data.task_id]: {
            vmId: selectedTestVm.id,
            vmName: selectedTestVm.name,
            status: 'queued',
            progress: 0,
            startTime: new Date().toISOString()
          }
        }));

        // Start polling for status
        startTestStatusPolling(response.data.task_id);

        setTestModalOpen(false);
        testForm.resetFields();
      }
    } catch (error) {
      console.error('Failed to start test:', error);
      message.error(error?.response?.data?.detail || 'Failed to start auto test');
    } finally {
      setStartingTest(false);
    }
  };

  const startTestStatusPolling = (taskId) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/api/tests/status/${taskId}`);
        const status = response.data;

        setRunningTests(prev => ({
          ...prev,
          [taskId]: {
            ...prev[taskId],
            status: status.status,
            progress: status.progress || 0,
            result: status.result,
            error: status.error
          }
        }));

        // Stop polling if test is completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          if (status.status === 'completed') {
            message.success(`Test ${taskId} completed successfully!`);
          } else {
            message.error(`Test ${taskId} failed: ${status.error || 'Unknown error'}`);
          }

          // Refresh VMs to update test metrics
          setTimeout(() => fetchVMs(), 1000);
        }
      } catch (error) {
        console.error('Failed to fetch test status:', error);
      }
    }, 5000); // Poll every 5 seconds

    setTestPollingInterval(interval);
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (testPollingInterval) {
        clearInterval(testPollingInterval);
      }
    };
  }, [testPollingInterval]);

  const openRunPreviousModal = async (vm) => {
    setSelectedTestVm(vm);
    setLoadingPreviousConfig(true);
    setRunPreviousModalOpen(true);

    try {
      const response = await axios.get(`${API_URL}/api/tests/previous/${vm.id}`);
      setPreviousTestConfig(response.data);

      // Pre-fill the form with the current docker tag
      const currentTag = response.data.config?.environment?.docker_tag || 'latest';
      runPreviousForm.setFieldsValue({
        docker_tag: currentTag
      });
    } catch (error) {
      message.error(error?.response?.data?.detail || 'No previous tests found for this VM');
      setRunPreviousModalOpen(false);
    } finally {
      setLoadingPreviousConfig(false);
    }
  };

  const runPreviousTest = async () => {
    try {
      const values = await runPreviousForm.validateFields();
      setStartingTest(true);

      const response = await axios.post(
        `${API_URL}/api/tests/rerun/${previousTestConfig.task_id}`,
        { docker_tag: values.docker_tag }
      );

      if (response.data.task_id) {
        message.success(`Test re-queued successfully! New Task ID: ${response.data.task_id}`);

        // Store the running test
        setRunningTests(prev => ({
          ...prev,
          [response.data.task_id]: {
            vmId: selectedTestVm.id,
            vmName: selectedTestVm.name,
            status: 'queued',
            progress: 0,
            startTime: new Date().toISOString()
          }
        }));

        // Start polling for status
        startTestStatusPolling(response.data.task_id);

        setRunPreviousModalOpen(false);
        runPreviousForm.resetFields();
        setPreviousTestConfig(null);
      }
    } catch (error) {
      console.error('Failed to re-run test:', error);
      message.error(error?.response?.data?.detail || 'Failed to re-run test');
    } finally {
      setStartingTest(false);
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
          <Tooltip title="Run automated tests in Jenkins-style Docker execution">
            <Button
              size="small"
              type="primary"
              icon={<ExperimentOutlined />}
              onClick={() => openTestModal(record)}
              style={{ background: '#52c41a', borderColor: '#52c41a' }}
            >
              Start
            </Button>
          </Tooltip>
          <Tooltip title="Re-run previous test with modified Docker tag">
            <Button
              size="small"
              type="default"
              icon={<ReloadOutlined />}
              onClick={() => openRunPreviousModal(record)}
            >
              Run Previous
            </Button>
          </Tooltip>
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

      {/* Running Tests Display */}
      {Object.keys(runningTests).length > 0 && (
        <Alert
          type="info"
          message={`Running Tests (${Object.keys(runningTests).length})`}
          description={
            <div>
              {Object.entries(runningTests).map(([taskId, test]) => (
                <div key={taskId} style={{ marginBottom: 8 }}>
                  <Typography.Text strong>{test.vmName}</Typography.Text>
                  <br />
                  <Typography.Text type="secondary">Task ID: {taskId}</Typography.Text>
                  <br />
                  <Typography.Text>Status: <Tag color={
                    test.status === 'running' ? 'processing' :
                    test.status === 'completed' ? 'success' :
                    test.status === 'failed' ? 'error' : 'default'
                  }>{test.status.toUpperCase()}</Tag></Typography.Text>
                  {test.progress > 0 && (
                    <div style={{ marginTop: 4 }}>
                      Progress: {test.progress}%
                    </div>
                  )}
                  {test.error && (
                    <Alert type="error" message={test.error} style={{ marginTop: 4 }} />
                  )}
                </div>
              ))}
            </div>
          }
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

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

      {/* Run Previous Test Modal */}
      <Modal
        title={`Run Previous Test${selectedTestVm ? ` - ${selectedTestVm.name}` : ''}`}
        open={runPreviousModalOpen}
        onOk={runPreviousTest}
        onCancel={() => {
          setRunPreviousModalOpen(false);
          runPreviousForm.resetFields();
          setPreviousTestConfig(null);
        }}
        okText="Run Test"
        confirmLoading={startingTest}
        width={600}
      >
        {loadingPreviousConfig ? (
          <Spin />
        ) : previousTestConfig ? (
          <>
            <Alert
              type="info"
              message="Quick Re-run with Modified Docker Tag"
              description="Modify only the Docker tag to quickly re-run the previous test configuration."
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Card size="small" title="Previous Test Configuration" style={{ marginBottom: 16 }}>
              <Typography.Text strong>Platform:</Typography.Text> {previousTestConfig.config?.environment?.platform || 'N/A'}<br />
              <Typography.Text strong>Test Suite:</Typography.Text> {previousTestConfig.config?.environment?.test_suite || 'N/A'}<br />
              <Typography.Text strong>Test Markers:</Typography.Text> {previousTestConfig.config?.environment?.test_markers || 'N/A'}<br />
              <Typography.Text strong>Execution Method:</Typography.Text> {previousTestConfig.config?.environment?.execution_method || 'N/A'}<br />
              <Typography.Text strong>Docker Image:</Typography.Text> {previousTestConfig.config?.environment?.docker_registry || 'docker.io'}/{previousTestConfig.config?.environment?.docker_image || 'N/A'}<br />
              <Typography.Text strong>Previous Status:</Typography.Text> <Tag color={
                previousTestConfig.status === 'completed' ? 'success' :
                previousTestConfig.status === 'failed' ? 'error' : 'default'
              }>{previousTestConfig.status?.toUpperCase()}</Tag>
            </Card>

            <Form form={runPreviousForm} layout="vertical">
              <Form.Item
                name="docker_tag"
                label="Docker Tag"
                rules={[{ required: true, message: 'Please enter docker tag' }]}
                tooltip="Modify the Docker tag to use a different version"
              >
                <Input placeholder="latest, v1.0.0, dev, etc." />
              </Form.Item>
            </Form>

            <Alert
              type="success"
              message="All other settings will remain the same"
              description="Only the Docker tag will be changed. VM IP, credentials, test suite, and all other parameters will be reused."
              showIcon
            />
          </>
        ) : (
          <Empty description="No previous test configuration available" />
        )}
      </Modal>

      {/* Auto Test Configuration Modal */}
      <Modal
        title={`Configure Auto Test${selectedTestVm ? ` - ${selectedTestVm.name}` : ''}`}
        open={testModalOpen}
        onOk={runAutoTest}
        onCancel={() => {
          setTestModalOpen(false);
          testForm.resetFields();
        }}
        okText="Start Test"
        confirmLoading={startingTest}
        width={700}
      >
        <Alert
          type="info"
          message="Jenkins-Style Docker Execution"
          description="This will execute tests on a Jenkins worker node using Docker containers, fetching configuration from lab config files."
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={testForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="platform"
                label="Platform"
                rules={[{ required: true, message: 'Please select a platform' }]}
              >
                <Select
                  options={[
                    { label: 'iOS', value: 'ios' },
                    { label: 'Android', value: 'android' }
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="execution_method"
                label="Execution Method"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { label: 'Docker (Recommended)', value: 'docker' },
                    { label: 'SSH Direct', value: 'ssh' }
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="test_suite"
                label="Test Suite"
                rules={[{ required: true, message: 'Please enter test suite name' }]}
              >
                <Input placeholder="FortiToken_Mobile" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="test_markers"
                label="Test Markers"
                tooltip="Pytest markers to filter tests (e.g., smoke, regression, sanity)"
                rules={[{ required: true, message: 'Please enter test markers' }]}
              >
                <Input placeholder="smoke" />
              </Form.Item>
            </Col>
          </Row>

          <Typography.Title level={5} style={{ marginTop: 16 }}>Docker Configuration</Typography.Title>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="docker_registry"
                label="Docker Registry"
                rules={[{ required: true }]}
              >
                <Input placeholder="docker.io" />
              </Form.Item>
            </Col>
            <Col span={10}>
              <Form.Item
                name="docker_image"
                label="Docker Image"
                rules={[{ required: true }]}
              >
                <Input placeholder="pytest-automation" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="docker_tag"
                label="Tag"
                rules={[{ required: true }]}
              >
                <Input placeholder="latest" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="timeout"
            label="Timeout (seconds)"
            rules={[{ required: true }]}
          >
            <InputNumber min={300} max={7200} style={{ width: '100%' }} />
          </Form.Item>
        </Form>

        <Alert
          type="warning"
          message="VM Configuration"
          description={
            selectedTestVm ? (
              <div>
                <Typography.Text strong>VM IP:</Typography.Text> {selectedTestVm.ip_address}<br />
                <Typography.Text strong>Username:</Typography.Text> {selectedTestVm.ssh_username}<br />
                <Typography.Text strong>Platform:</Typography.Text> {selectedTestVm.platform}<br />
                <Typography.Text strong>Version:</Typography.Text> {selectedTestVm.version}
              </div>
            ) : 'No VM selected'
          }
          showIcon
          style={{ marginTop: 16 }}
        />
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
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [qrModalVisible, setQrModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [qrData, setQrData] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [editingFileName, setEditingFileName] = useState('');
  const [fileList, setFileList] = useState([]);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/`);
      setFiles(response.data);
    } catch (error) {
      message.error('Failed to fetch files');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('Please select at least one file');
      return;
    }

    const formData = new FormData();
    fileList.forEach(file => {
      formData.append('files', file.originFileObj || file);
    });

    setLoading(true);
    try {
      await axios.post(`${API_URL}/api/files/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      message.success('Files uploaded successfully');
      setUploadModalVisible(false);
      setFileList([]);
      fetchFiles();
    } catch (error) {
      message.error('Failed to upload files');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (filename) => {
    window.open(`${API_URL}/uploads/${encodeURIComponent(filename)}`, '_blank');
  };

  const handleDelete = async (filename) => {
    setLoading(true);
    try {
      await axios.delete(`${API_URL}/api/files/file/${encodeURIComponent(filename)}`);
      message.success('File deleted successfully');
      fetchFiles();
    } catch (error) {
      message.error('Failed to delete file');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateQR = async (filename) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/qr/${encodeURIComponent(filename)}`);
      setQrData(response.data);
      setQrModalVisible(true);
    } catch (error) {
      message.error('Failed to generate QR code');
    } finally {
      setLoading(false);
    }
  };

  const handleEditFile = async (filename) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/file/${encodeURIComponent(filename)}`);
      setFileContent(response.data.content);
      setEditingFileName(filename);
      setSelectedFile(filename);
      form.setFieldsValue({
        newName: filename,
        content: response.data.content
      });
      setEditModalVisible(true);
    } catch (error) {
      if (error.response?.status === 415) {
        message.error('This file is not a text file and cannot be edited');
      } else {
        message.error('Failed to read file');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSaveFile = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      await axios.put(`${API_URL}/api/files/file/${encodeURIComponent(editingFileName)}`, {
        newName: values.newName !== editingFileName ? values.newName : undefined,
        content: values.content !== fileContent ? values.content : undefined
      });

      message.success('File updated successfully');
      setEditModalVisible(false);
      form.resetFields();
      fetchFiles();
    } catch (error) {
      if (error.response) {
        message.error('Failed to update file');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (text) => (
        <Space>
          <FileOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      sorter: (a, b) => a.size - b.size,
      render: (size) => formatFileSize(size),
    },
    {
      title: 'Upload Date',
      dataIndex: 'uploadDate',
      key: 'uploadDate',
      sorter: (a, b) => new Date(a.uploadDate) - new Date(b.uploadDate),
      render: (date) => formatDate(date),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="Download">
            <Button
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.name)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="Generate QR Code">
            <Button
              icon={<QrcodeOutlined />}
              onClick={() => handleGenerateQR(record.name)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="View/Edit">
            <Button
              icon={<EditOutlined />}
              onClick={() => handleEditFile(record.name)}
              size="small"
            />
          </Tooltip>
          <Popconfirm
            title="Are you sure you want to delete this file?"
            onConfirm={() => handleDelete(record.name)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                icon={<DeleteOutlined />}
                danger
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const uploadProps = {
    multiple: true,
    fileList: fileList,
    beforeUpload: (file) => {
      setFileList([...fileList, file]);
      return false;
    },
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>File Browser</h1>
        <Space>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            Upload Files
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchFiles}
          >
            Refresh
          </Button>
        </Space>
      </div>

      <Card>
        <Table
          dataSource={files}
          columns={columns}
          rowKey="name"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Upload Modal */}
      <Modal
        title="Upload Files"
        open={uploadModalVisible}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
        }}
        okText="Upload"
        confirmLoading={loading}
      >
        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">Click or drag files to this area to upload</p>
          <p className="ant-upload-hint">Support for single or bulk upload</p>
        </Upload.Dragger>
      </Modal>

      {/* QR Code Modal */}
      <Modal
        title="QR Code for Download"
        open={qrModalVisible}
        onCancel={() => {
          setQrModalVisible(false);
          setQrData(null);
        }}
        footer={[
          <Button key="close" onClick={() => setQrModalVisible(false)}>
            Close
          </Button>
        ]}
      >
        {qrData && (
          <div style={{ textAlign: 'center' }}>
            <p><strong>File:</strong> {qrData.filename}</p>
            <Image
              src={qrData.qrDataUrl}
              alt="QR Code"
              style={{ maxWidth: '100%' }}
              preview={false}
            />
            <p style={{ marginTop: 16, wordBreak: 'break-all' }}>
              <strong>Download URL:</strong><br />
              <a href={qrData.downloadUrl} target="_blank" rel="noopener noreferrer">
                {qrData.downloadUrl}
              </a>
            </p>
          </div>
        )}
      </Modal>

      {/* Edit File Modal */}
      <Modal
        title={`Edit File: ${editingFileName}`}
        open={editModalVisible}
        onOk={handleSaveFile}
        onCancel={() => {
          setEditModalVisible(false);
          form.resetFields();
        }}
        okText="Save"
        confirmLoading={loading}
        width={800}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="File Name"
            name="newName"
            rules={[{ required: true, message: 'Please enter a file name' }]}
          >
            <Input placeholder="Enter new file name" />
          </Form.Item>
          <Form.Item
            label="Content"
            name="content"
            rules={[{ required: true, message: 'Content cannot be empty' }]}
          >
            <Input.TextArea
              rows={15}
              placeholder="File content"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Form>
      </Modal>
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
    { key: '/workers', icon: <MonitorOutlined />, label: 'Worker Dashboard', path: '/workers' },
    { key: '/vms', icon: <CloudServerOutlined />, label: 'Virtual Machines', path: '/vms' },
    { key: '/devices', icon: <MobileOutlined />, label: 'Devices', path: '/devices' },
    { key: '/jenkins', icon: <ClusterOutlined />, label: 'Jenkins Nodes', path: '/jenkins' },
    { key: '/apks', icon: <AppstoreOutlined />, label: 'APK Manager', path: '/apks' },
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
          <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/workers" element={<WorkerDashboard />} />
              <Route path="/vms" element={<VMs />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/jenkins" element={<JenkinsNodes />} />
              <Route path="/apks" element={<ApkBrowser />} />
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
