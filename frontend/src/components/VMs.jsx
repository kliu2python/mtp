import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message
} from 'antd';
import {
  BarChartOutlined,
  CodeOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { API_URL } from '../constants';

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
  const [availableApks, setAvailableApks] = useState([]);
  const [loadingApks, setLoadingApks] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [runningTests, setRunningTests] = useState({});
  const [testPollingInterval, setTestPollingInterval] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [appSourceType, setAppSourceType] = useState('file'); // 'file' or 'version'
  const [testTemplates, setTestTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

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

  const fetchApksForPlatform = async (platform) => {
    setLoadingApks(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/`, {});
      console.log(response.data)
      
      const files = response.data;
      const apkFiles = files.filter((file) => {
        const fileName = file?.name?.toLowerCase() || '';
        return platform === 'ios' ? fileName.endsWith('.ipa') : fileName.endsWith('.apk');
      });
      setAvailableApks(apkFiles);
    } catch (error) {
      console.error('Failed to fetch APKs:', error);
      message.error('Failed to load app versions');
      setAvailableApks([]);
    } finally {
      setLoadingApks(false);
    }
  };

  const openTestModal = (vm) => {
    setSelectedTestVm(vm);
    testForm.resetFields();
    setCurrentStep(0);
    setAppSourceType('file');
    // Set default values based on VM
    const defaultPlatform = vm.platform === 'FortiGate' ? 'ios' : 'android';
    setSelectedPlatform(defaultPlatform);
    testForm.setFieldsValue({
      platform: defaultPlatform,
      test_scope: 'smoke',
      environment: 'qa',
      test_suite: 'FortiToken_Mobile',
      timeout: 3600,
      docker_tag: 'latest'
    });
    // Fetch APKs for the default platform
    fetchApksForPlatform(defaultPlatform);
    setTestModalOpen(true);
  };

  const handleNextStep = async () => {
    try {
      // Validate fields for current step before proceeding
      if (currentStep === 0) {
        // Step 1: Platform & App Version
        await testForm.validateFields(['platform', appSourceType === 'file' ? 'apk_id' : 'app_version']);
      } else if (currentStep === 1) {
        // Step 2: Test Configuration
        await testForm.validateFields(['test_scope', 'test_suite', 'environment']);
      }
      // If validation passes, move to next step
      setCurrentStep(currentStep + 1);
    } catch (error) {
      // Validation failed, show error message
      message.error('Please fill in all required fields before proceeding');
    }
  };

  const runAutoTest = async () => {
    try {
      const values = await testForm.validateFields();
      setStartingTest(true);

      const testConfig = {
        name: `Auto Test - ${selectedTestVm.name}`,
        vm_id: selectedTestVm.id,
        apk_id: appSourceType === 'file' ? values.apk_id : null,
        app_version: appSourceType === 'version' ? values.app_version : null,
        test_scope: values.test_scope,
        environment: values.environment,
        platform: values.platform,
        execution_method: 'docker', // Always use Docker execution
        test_suite: values.test_suite,
        docker_config: {
          registry: 'docker.io',
          image: 'pytest-automation',
          tag: values.docker_tag
        },
        timeout: values.timeout,
        save_as_template: values.save_as_template,
        template_name: values.template_name
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
      setSavingVm(false);
      fetchVMs();
    } catch (error) {
      message.error('Failed to save virtual machine');
      setSavingVm(false);
    }
  };

  const hasSshDetails = selectedVm?.ip_address && selectedVm?.ssh_username && selectedVm?.ssh_password;

  const openSshModal = (vm) => {
    setSelectedVm(vm);
    setSshModalOpen(true);
    setSshError(null);
  };

  const closeActiveSocket = () => {
    if (sshSocketRef.current) {
      sshSocketRef.current.close();
      sshSocketRef.current = null;
    }
  };

  useEffect(() => {
    if (!sshModalOpen || !selectedVm) return;

    const terminal = new Terminal({
      cursorBlink: true,
      rows: 25,
      convertEol: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#ffffff',
        cursor: '#ffffff',
      },
    });
    sshTerminalInstanceRef.current = terminal;

    const fitAddon = new FitAddon();
    sshFitAddonRef.current = fitAddon;

    terminal.loadAddon(fitAddon);
    terminal.open(sshTerminalRef.current);
    fitAddon.fit();

    const socketUrl = `${API_URL.replace('http', 'ws')}/api/vms/${selectedVm.id}/ssh/ws`;
    const socket = new WebSocket(socketUrl);
    sshSocketRef.current = socket;

    setSshConnecting(true);
    terminal.write('Connecting to SSH...\r\n');

    const handleResize = () => {
      fitAddon.fit();
      const { rows, cols } = terminal;
      socket.send(JSON.stringify({ type: 'resize', rows, cols }));
    };

    window.addEventListener('resize', handleResize);

    const dataDisposable = terminal.onData((data) => {
      socket.send(JSON.stringify({ type: 'input', data }));
    });

    socket.onopen = () => {
      setSshConnecting(false);
      const { rows, cols } = terminal;
      socket.send(JSON.stringify({ type: 'resize', rows, cols }));
      terminal.write('Connected!\r\n');
      if (!hasSshDetails) {
        terminal.write('Warning: VM SSH credentials not fully set.\r\n');
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'output') {
          terminal.write(data.data);
        }
      } catch (error) {
        console.error('Error parsing SSH message:', error);
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

  const formatApkSize = (bytes) => {
    if (!bytes || bytes <= 0) return 'Unknown size';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatApkDate = (dateString) => {
    if (!dateString) return 'Unknown upload time';
    return new Date(dateString).toLocaleString();
  };

  const appFileOptions = availableApks.map((apk) => ({
    value: apk.name,
    label: apk.name,
    searchText: [
      apk.name,
      apk.version_name ? `v${apk.version_name}` : null,
      apk.file_path,
    ]
      .filter(Boolean)
      .join(' ')?.toLowerCase(),
    apk,
  }));

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
          <Tooltip title="Run automated tests with Docker execution">
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

  const testTemplatesColumns = [
    {
      title: 'Template Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
    },
    {
      title: 'Test Scope',
      dataIndex: 'test_scope',
      key: 'test_scope',
    },
    {
      title: 'Test Suite',
      dataIndex: 'test_suite',
      key: 'test_suite',
    },
    {
      title: 'Environment',
      dataIndex: 'environment',
      key: 'environment',
    },
    {
      title: 'Docker Tag',
      dataIndex: ['docker_config', 'tag'],
      key: 'docker_tag',
      render: (value) => value || 'latest',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type="primary"
            onClick={() => {
              testForm.setFieldsValue({
                ...record,
                docker_tag: record.docker_config?.tag || 'latest',
              });
              setAppSourceType(record.app_version ? 'version' : 'file');
              setSelectedPlatform(record.platform);
              setCurrentStep(1);
            }}
          >
            Use Template
          </Button>
          <Popconfirm
            title="Delete Template"
            description="This action cannot be undone."
            onConfirm={async () => {
              try {
                await axios.delete(`${API_URL}/api/tests/templates/${record.id}`);
                message.success('Template deleted');
                fetchTestTemplates();
              } catch (error) {
                message.error('Failed to delete template');
              }
            }}
            okText="Delete"
            okType="danger"
          >
            <Button size="small" danger>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const runningTestColumns = [
    {
      title: 'Task ID',
      dataIndex: 'taskId',
      key: 'taskId',
    },
    {
      title: 'VM Name',
      dataIndex: 'vmName',
      key: 'vmName',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'default';
        let icon = null;
        switch (status) {
          case 'completed':
            color = 'green';
            icon = <span>✅</span>;
            break;
          case 'failed':
            color = 'red';
            icon = <span>❌</span>;
            break;
          case 'running':
            color = 'blue';
            icon = <span>⏳</span>;
            break;
          default:
            color = 'default';
            icon = <span>⏺️</span>;
        }
        return (
          <Space>
            <Tag color={color}>
              {icon} {status?.toUpperCase()}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress) => <Progress percent={Math.round(progress)} size="small" />,
    },
  ];

  const fetchTestTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const response = await axios.get(`${API_URL}/api/tests/templates`);
      setTestTemplates(response.data || []);
    } catch (error) {
      if (error.response?.status === 404) {
        setTestTemplates([]);
      } else {
        message.error('Failed to load test templates');
      }
    } finally {
      setLoadingTemplates(false);
    }
  };

  useEffect(() => {
    if (testModalOpen) {
      fetchTestTemplates();
    }
  }, [testModalOpen]);

  const renderRunningTests = () => {
    const runningTestsArray = Object.entries(runningTests).map(([taskId, test]) => ({
      key: taskId,
      taskId,
      ...test,
    }));

    if (runningTestsArray.length === 0) {
      return <Empty description="No running tests" />;
    }

    return (
      <Table
        dataSource={runningTestsArray}
        columns={runningTestColumns}
        pagination={false}
        size="small"
      />
    );
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="Total VMs" value={vms.length} loading={loading} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Running"
              value={vms.filter(vm => vm.status === 'running').length}
              loading={loading}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Stopped"
              value={vms.filter(vm => vm.status === 'stopped').length}
              loading={loading}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Avg Pass Rate" value={vms.reduce((sum, vm) => sum + (vm.pass_rate || 0), 0) / (vms.length || 1)} loading={loading} suffix="%" />
          </Card>
        </Col>
      </Row>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Virtual Machines</h1>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchVMs} loading={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            Add VM
          </Button>
        </Space>
      </div>

      <Table dataSource={vms} columns={columns} rowKey="id" loading={loading} />

      <Divider orientation="left">Running Tests</Divider>
      {renderRunningTests()}

      <Modal
        title={vmModalMode === 'edit' ? 'Edit Virtual Machine' : 'Create Virtual Machine'}
        open={vmModalOpen}
        onCancel={() => setVmModalOpen(false)}
        onOk={handleSaveVm}
        confirmLoading={savingVm}
        okText={vmModalMode === 'edit' ? 'Update' : 'Create'}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please input the VM name' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Platform"
            name="platform"
            rules={[{ required: true, message: 'Please select platform' }]}
          >
            <Select
              options={[
                { label: 'FortiGate', value: 'FortiGate' },
                { label: 'FortiAuthenticator', value: 'FortiAuthenticator' }
              ]}
            />
          </Form.Item>
          <Form.Item
            label="Version"
            name="version"
            rules={[{ required: true, message: 'Please input version' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Test Priority"
            name="test_priority"
            rules={[{ required: true, message: 'Please input test priority' }]}
          >
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="IP Address" name="ip_address">
            <Input />
          </Form.Item>
          <Form.Item label="SSH Username" name="ssh_username">
            <Input />
          </Form.Item>
          <Form.Item label="SSH Password" name="ssh_password">
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`SSH Terminal - ${selectedVm?.name}`}
        open={sshModalOpen}
        onCancel={() => {
          setSshModalOpen(false);
          setSelectedVm(null);
          setSshError(null);
        }}
        footer={null}
        width={800}
        bodyStyle={{ height: 500, overflow: 'hidden' }}
        destroyOnClose
      >
        {sshError && <Alert message={sshError} type="error" showIcon style={{ marginBottom: 16 }} />}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12, gap: 8 }}>
          <Tag color={hasSshDetails ? 'green' : 'red'}>
            {hasSshDetails ? 'SSH credentials configured' : 'SSH credentials incomplete'}
          </Tag>
          {sshConnecting && <Spin size="small" />}<Tag color="blue">Websocket-based SSH</Tag>
        </div>
        <div
          ref={sshTerminalRef}
          style={{ width: '100%', height: '100%', backgroundColor: '#1e1e1e', padding: 8 }}
        />
      </Modal>

      <Drawer
        title={`Logs - ${selectedVm?.name}`}
        placement="right"
        width={600}
        onClose={() => {
          setLogsDrawerOpen(false);
          setSelectedVm(null);
          setLogs([]);
        }}
        open={logsDrawerOpen}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} size="small" onClick={refreshLogs} disabled={logsLoading}>
              Refresh
            </Button>
            <Button size="small" onClick={() => setLogs([])} disabled={logsLoading}>
              Clear
            </Button>
          </Space>
        }
      >
        {logsLoading ? (
          <Spin />
        ) : (
          <pre style={{ background: '#f5f5f5', padding: 12, height: '100%', overflow: 'auto' }}>
            {logs.join('\n')}
          </pre>
        )}
      </Drawer>

      <Drawer
        title={`Metrics - ${selectedVm?.name}`}
        placement="right"
        width={500}
        onClose={() => {
          setMetricsDrawerOpen(false);
          setSelectedVm(null);
          setMetrics(null);
        }}
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
            <strong>CPU Usage:</strong> {metrics.cpu_usage ?? metrics.cpu_percent ?? 0}%<br />
            <strong>Memory Usage:</strong> {metrics.memory_usage ?? metrics.memory_percent ?? 0}%<br />
            <strong>Disk Usage:</strong> {metrics.disk_usage ?? metrics.disk_percent ?? 0}%
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary">No metrics available.</Typography.Text>
        )}
      </Drawer>

      <Modal
        title={
          testModalOpen && selectedTestVm
            ? `Configure Auto Test - ${selectedTestVm.name} (Step ${currentStep + 1}/3)`
            : 'Configure Auto Test'
        }
        open={testModalOpen}
        onCancel={() => {
          setTestModalOpen(false);
          testForm.resetFields();
          setCurrentStep(0);
        }}
        footer={[
          currentStep > 0 && (
            <Button key="back" onClick={() => setCurrentStep(currentStep - 1)}>
              Previous
            </Button>
          ),
          currentStep < 2 && (
            <Button key="next" type="primary" onClick={handleNextStep}>
              Next
            </Button>
          ),
          currentStep === 2 && (
            <Button key="submit" type="primary" onClick={runAutoTest} loading={startingTest}>
              Start Test
            </Button>
          ),
          <Button key="cancel" onClick={() => {
            setTestModalOpen(false);
            testForm.resetFields();
            setCurrentStep(0);
          }}>
            Cancel
          </Button>
        ]}
        width={800}
      >
        <Form form={testForm} layout="vertical">
          {currentStep === 0 && (
            <>
              <Alert
                type="info"
                message="Step 1: Platform & App Version"
                description="Select the platform and specify the app version to test."
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                name="platform"
                label="Platform"
                rules={[{ required: true, message: 'Please select a platform' }]}
              >
                <Select
                  onChange={(value) => {
                    setSelectedPlatform(value);
                    fetchApksForPlatform(value);
                    testForm.setFieldsValue({ apk_id: undefined });
                  }}
                  options={[
                    { label: 'iOS', value: 'ios' },
                    { label: 'Android', value: 'android' }
                  ]}
                />
              </Form.Item>

              <Form.Item label="App Version Source">
                <Radio.Group
                  value={appSourceType}
                  onChange={(e) => {
                    setAppSourceType(e.target.value);
                    testForm.setFieldsValue({ apk_id: undefined, app_version: undefined });
                  }}
                >
                  <Radio value="file">Select from Files</Radio>
                  <Radio value="version">Enter Version Number</Radio>
                </Radio.Group>
              </Form.Item>

              {appSourceType === 'file' ? (
                <Form.Item
                  name="apk_id"
                  label="App File"
                  rules={[{ required: true, message: 'Please select an app file' }]}
                  tooltip="Select a specific app version from uploaded files"
                >
                  <Select
                    placeholder="Select app file"
                    loading={loadingApks}
                    disabled={!selectedPlatform}
                    options={appFileOptions}
                    optionRender={(option) => {
                      const apk = option?.data?.apk || option?.apk;
                      return (
                        <Space direction="vertical" size={0}>
                          <Typography.Text strong>{option.value}</Typography.Text>
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            {[apk?.version_name ? `v${apk.version_name}` : null, apk?.file_path ? `Path: ${apk.file_path}` : null, `Size: ${formatApkSize(apk?.file_size)}`]
                              .filter(Boolean)
                              .join(' • ')}
                          </Typography.Text>
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            Uploaded: {formatApkDate(apk?.created_at)}
                          </Typography.Text>
                        </Space>
                      );
                    }}
                    showSearch
                    optionFilterProp="searchText"
                    filterOption={(input, option) => {
                      const searchText = input.toLowerCase();
                      const optionText = (option?.searchText || '').toLowerCase();
                      return optionText.includes(searchText);
                    }}
                  />
                </Form.Item>
              ) : (
                <Form.Item
                  name="app_version"
                  label="App Version"
                  rules={[{ required: true, message: 'Please enter app version' }]}
                  tooltip="Enter build number, 'dev', 'released', or specific version number"
                >
                  <Input placeholder="e.g., 1.2.3, build-1234, dev, released" />
                </Form.Item>
              )}

              {selectedTestVm && (
                <Alert
                  type="info"
                  message="VM Configuration"
                  description={
                    <div>
                      <Typography.Text strong>VM IP:</Typography.Text> {selectedTestVm.ip_address}<br />
                      <Typography.Text strong>Platform:</Typography.Text> {selectedTestVm.platform}<br />
                      <Typography.Text strong>Version:</Typography.Text> {selectedTestVm.version}
                    </div>
                  }
                  showIcon
                  style={{ marginTop: 16 }}
                />
              )}
            </>
          )}

          {currentStep === 1 && (
            <>
              <Alert
                type="info"
                message="Step 2: Test Configuration"
                description="Configure what tests to run and in which environment."
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                name="test_scope"
                label="Test Scope"
                rules={[{ required: true, message: 'Please select test scope' }]}
                tooltip="Select the test scope to run"
              >
                <Select
                  placeholder="Select test scope"
                  options={[
                    { label: 'Smoke Tests', value: 'smoke' },
                    { label: 'Regression Tests', value: 'regression' },
                    { label: 'Integration Tests', value: 'integration' },
                    { label: 'Critical Tests', value: 'critical' },
                    { label: 'Release Tests', value: 'release' }
                  ]}
                />
              </Form.Item>

              <Form.Item
                name="test_suite"
                label="Test Suite"
                rules={[{ required: true, message: 'Please enter test suite name' }]}
                tooltip="Enter the name of the test suite to execute"
              >
                <Input placeholder="FortiToken_Mobile" />
              </Form.Item>

              <Form.Item
                name="environment"
                label="Environment"
                rules={[{ required: true, message: 'Please select environment' }]}
                tooltip="Select the test environment"
              >
                <Select
                  placeholder="Select environment"
                  options={[
                    { label: 'QA Environment', value: 'qa' },
                    { label: 'Release Environment', value: 'release' },
                    { label: 'Production Environment', value: 'production' }
                  ]}
                />
              </Form.Item>
            </>
          )}

          {currentStep === 2 && (
            <>
              <Alert
                type="info"
                message="Step 3: Execution Settings"
                description="Configure Docker image tag, timeout, and save as template for future use."
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item
                name="docker_tag"
                label="Docker Tag"
                rules={[{ required: true, message: 'Please enter docker tag' }]}
                tooltip="Tag for the pytest-automation Docker image"
                initialValue="latest"
              >
                <Input placeholder="latest" />
              </Form.Item>

              <Form.Item
                name="timeout"
                label="Timeout (seconds)"
                rules={[{ required: true, message: 'Please enter timeout' }]}
                initialValue={3600}
                tooltip="Maximum execution time before test is terminated"
              >
                <InputNumber min={60} max={7200} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="save_as_template"
                valuePropName="checked"
              >
                <Checkbox>Save this configuration as a template</Checkbox>
              </Form.Item>

              <Form.Item
                name="template_name"
                label="Template Name"
                dependencies={['save_as_template']}
                rules={[
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!getFieldValue('save_as_template')) {
                        return Promise.resolve();
                      }
                      if (!value) {
                        return Promise.reject(new Error('Please enter template name'));
                      }
                      return Promise.resolve();
                    },
                  }),
                ]}
              >
                <Input placeholder="e.g., iOS smoke tests" />
              </Form.Item>

              <Divider orientation="left">Saved Templates</Divider>
              <Table
                dataSource={testTemplates}
                columns={testTemplatesColumns}
                rowKey="id"
                loading={loadingTemplates}
                size="small"
              />
            </>
          )}
        </Form>
      </Modal>

      <Modal
        title={`Run Previous Test${selectedTestVm ? ` - ${selectedTestVm.name}` : ''}`}
        open={runPreviousModalOpen}
        onCancel={() => {
          setRunPreviousModalOpen(false);
          runPreviousForm.resetFields();
          setPreviousTestConfig(null);
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setRunPreviousModalOpen(false);
            runPreviousForm.resetFields();
            setPreviousTestConfig(null);
          }}>
            Cancel
          </Button>,
          <Button key="run" type="primary" onClick={runPreviousTest} loading={startingTest}>
            Re-run Test
          </Button>
        ]}
        width={700}
      >
        {loadingPreviousConfig ? (
          <Spin />
        ) : previousTestConfig ? (
          <>
            <Card size="small" title="Previous Test Configuration" style={{ marginBottom: 16 }}>
              <Typography.Text strong>Test Suite:</Typography.Text> {previousTestConfig.config?.test_suite || 'N/A'}<br />
              <Typography.Text strong>Environment:</Typography.Text> {previousTestConfig.config?.environment?.name || 'N/A'}<br />
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
    </div>
  );
};

export default VMs;
