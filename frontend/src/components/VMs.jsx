import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Dropdown,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Radio,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Typography,
  message
} from 'antd';
import {
  CodeOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  GlobalOutlined,
  PlusOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { API_URL, DEVICE_NODES_API_BASE_URL } from '../constants';

const VMs = () => {
  const [vms, setVms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [vmModalOpen, setVmModalOpen] = useState(false);
  const [vmModalMode, setVmModalMode] = useState('create');
  const [savingVm, setSavingVm] = useState(false);
  const [form] = Form.useForm();
  const [cloudForm] = Form.useForm();
  const [editingVm, setEditingVm] = useState(null);
  const [selectedVm, setSelectedVm] = useState(null);
  const [sshModalOpen, setSshModalOpen] = useState(false);
  const [sshModalReady, setSshModalReady] = useState(false);
  const [logsDrawerOpen, setLogsDrawerOpen] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [metricsDrawerOpen, setMetricsDrawerOpen] = useState(false);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [webDrawerOpen, setWebDrawerOpen] = useState(false);
  const [webLoadError, setWebLoadError] = useState(null);
  const [webAccessUrl, setWebAccessUrl] = useState('');
  const [webEmbedAllowed, setWebEmbedAllowed] = useState(true);
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
  const [testPollingInterval, setTestPollingInterval] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [appSourceType, setAppSourceType] = useState('file'); // 'file' or 'version'
  const [vmSearch, setVmSearch] = useState('');
  const [testTemplates, setTestTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [deviceType, setDeviceType] = useState('physical');
  const [deviceOptions, setDeviceOptions] = useState([]);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [cloudServices, setCloudServices] = useState([]);
  const [cloudModalOpen, setCloudModalOpen] = useState(false);
  const [fetchingCloudVersion, setFetchingCloudVersion] = useState(false);
  const [refreshingTestbed, setRefreshingTestbed] = useState(false);

  // Run Previous states
  const [runPreviousModalOpen, setRunPreviousModalOpen] = useState(false);
  const [runPreviousForm] = Form.useForm();
  const [previousTestConfig, setPreviousTestConfig] = useState(null);
  const [loadingPreviousConfig, setLoadingPreviousConfig] = useState(false);

  useEffect(() => {
    refreshTestbed();
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

  const stopVM = async (vmId) => {
    try {
      await axios.post(`${API_URL}/api/vms/${vmId}/stop`);
      message.success('VM stopped successfully');
      fetchVMs();
    } catch (error) {
      message.error('Failed to stop VM');
    }
  };

  const refreshCloudServiceVersions = async () => {
    if (!cloudServices.length) return;

    const updatedServices = await Promise.all(
      cloudServices.map(async (service) => {
        if (!service.client_ip) return service;

        try {
          const { data } = await axios.get(`${API_URL}/api/cloud/version`, {
            params: { client_ip: service.client_ip },
          });

          const latestVersion = data?.version || service.server_version || service.version;

          return {
            ...service,
            server_version: latestVersion,
            version: latestVersion,
          };
        } catch (error) {
          return service;
        }
      })
    );

    setCloudServices(updatedServices);
  };

  const refreshTestbed = async () => {
    try {
      setRefreshingTestbed(true);
      await Promise.all([fetchVMs(), refreshCloudServiceVersions()]);
    } finally {
      setRefreshingTestbed(false);
    }
  };

  const fetchApksForPlatform = async (platform) => {
    setLoadingApks(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/`, {});
      
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
    setDeviceType('physical');
    // Set default values based on VM
    const defaultPlatform = vm.platform === 'FortiGate' ? 'ios' : 'android';
    setSelectedPlatform(defaultPlatform);
    testForm.setFieldsValue({
      platform: defaultPlatform,
      test_scope: 'smoke',
      environment: 'qa',
      test_suite: 'FortiToken_Mobile',
      timeout: 3600,
      docker_tag: 'latest',
      device_type: 'physical'
    });
    // Fetch APKs for the default platform
    fetchApksForPlatform(defaultPlatform);
    fetchAvailableDevices(defaultPlatform);
    setTestModalOpen(true);
  };

  useEffect(() => {
    if (selectedPlatform === 'ios' && deviceType === 'emulator') {
      setDeviceType('physical');
      testForm.setFieldsValue({ device_type: 'physical', emulator_version: undefined });
    }
  }, [selectedPlatform, deviceType, testForm]);

  const handleNextStep = async () => {
    try {
      // Validate fields for current step before proceeding
      if (currentStep === 0) {
        // Step 1: Platform & App Version
        const validationFields = ['platform', 'device_type'];
        validationFields.push(appSourceType === 'file' ? 'apk_id' : 'app_version');
        if (deviceType === 'physical') {
          validationFields.push('device_id');
        } else {
          validationFields.push('emulator_version');
        }
        await testForm.validateFields(validationFields);
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
        device_type: values.device_type,
        device_id: values.device_type === 'physical' ? values.device_id : null,
        emulator_version: values.device_type === 'emulator' ? values.emulator_version : null,
        save_as_template: values.save_as_template,
        template_name: values.template_name
      };

      const response = await axios.post(`${API_URL}/api/tests/execute`, testConfig);

      if (response.data.task_id) {
        message.success(`Test queued successfully! Task ID: ${response.data.task_id}`);

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

  const openCloudModal = () => {
    cloudForm.resetFields();
    setCloudModalOpen(true);
  };

  const handleAddNewSelection = ({ key }) => {
    if (key === 'vm') {
      openCreateModal();
      return;
    }

    openCloudModal();
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
      web_url: vm.web_url,
      web_username: vm.web_username,
      web_password: vm.web_password,
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

  const getCloudServiceDisplayName = (service) =>
    service.server_dns || service.server_ip || service.client_ip || 'Cloud Service';

  const handleSaveCloudService = async () => {
    try {
      const values = await cloudForm.validateFields();
      const {
        server_ip: serverIp,
        server_dns: serverDns,
        client_ip: clientIp,
        server_version: serverVersion,
      } = values;

      const newService = {
        id: Date.now(),
        name: getCloudServiceDisplayName(values),
        server_ip: serverIp,
        server_dns: serverDns,
        client_ip: clientIp,
        server_version: serverVersion,
      };

      setCloudServices((prev) => [...prev, newService]);
      setCloudModalOpen(false);
      message.success('Cloud service added');
    } catch (error) {
      if (error.errorFields) return;
      message.error('Failed to save cloud service');
    }
  };

  const detectCloudVersion = async () => {
    const { client_ip: clientIp } = cloudForm.getFieldsValue();

    if (!clientIp) {
      message.warning('Please provide the client IP before fetching the version.');
      return;
    }

    try {
      setFetchingCloudVersion(true);
      const { data } = await axios.get(`${API_URL}/api/cloud/version`, {
        params: { client_ip: clientIp },
      });
      const detectedVersion = data?.version || 'Unknown';
      cloudForm.setFieldsValue({ server_version: detectedVersion });
      const matchedHost = data?.matched_host ? ` from ${data.matched_host}` : '';
      message.success(`Server version fetched automatically${matchedHost}`);
    } catch (error) {
      message.warning('Unable to fetch server version automatically. You can enter it manually.');
    } finally {
      setFetchingCloudVersion(false);
    }
  };

  const removeCloudService = (serviceId) => {
    setCloudServices((prev) => prev.filter((service) => service.id !== serviceId));
  };

  const openCloudTestModal = (service) => {
    const cloudTestTarget = {
      id: service.id,
      name: service.name || getCloudServiceDisplayName(service),
      platform: service.platform || 'Cloud',
      version: service.server_version || 'N/A',
      ip_address: service.server_ip || service.client_ip,
    };

    openTestModal(cloudTestTarget);
  };

  const hasSshDetails = selectedVm?.ip_address && selectedVm?.ssh_username && selectedVm?.ssh_password;

  const normalizeToHttps = (url) => {
    try {
      const parsed = new URL(url);
      parsed.protocol = 'https:';
      return parsed.toString();
    } catch (error) {
      // If the URL constructor fails, fall back to the raw value.
      return url;
    }
  };

  const openWebDrawer = (vm) => {
    const baseUrl = vm.web_url || (vm.ip_address ? `http://${vm.ip_address}` : null);
    const resolvedUrl = baseUrl ? normalizeToHttps(baseUrl) : null;
    if (!resolvedUrl) {
      message.warning('No web access URL configured for this VM');
      return;
    }

    let embeddable = true;
    try {
      const parsedUrl = new URL(resolvedUrl);
      embeddable = parsedUrl.origin === window.location.origin;
    } catch (error) {
      embeddable = false;
    }

    setSelectedVm(vm);
    setWebAccessUrl(resolvedUrl);
    setWebEmbedAllowed(embeddable);
    setWebLoadError(null);
    setWebDrawerOpen(true);
  };

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
    if (!sshModalOpen || !sshModalReady || !selectedVm) return;

    const terminalContainer = sshTerminalRef.current;
    if (!terminalContainer) {
      setSshError('Unable to initialize SSH terminal. Please try reopening the modal.');
      return undefined;
    }

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
    terminal.open(terminalContainer);
    fitAddon.fit();

    const socketUrl = `${API_URL.replace('http', 'ws')}/api/vms/${selectedVm.id}/ssh/ws`;
    const socket = new WebSocket(socketUrl);
    sshSocketRef.current = socket;

    setSshConnecting(true);
    terminal.write('Connecting to SSH...\r\n');

    const safeSend = (payload) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(payload);
      }
    };

    const handleResize = () => {
      fitAddon.fit();
      const { rows, cols } = terminal;
      safeSend(JSON.stringify({ type: 'resize', rows, cols }));
    };

    window.addEventListener('resize', handleResize);

    const dataDisposable = terminal.onData((data) => {
      safeSend(JSON.stringify({ type: 'input', data }));
    });

    socket.onopen = () => {
      setSshConnecting(false);
      const { rows, cols } = terminal;
      safeSend(JSON.stringify({ type: 'resize', rows, cols }));
      terminal.write('Connected!\r\n');
      if (!hasSshDetails) {
        terminal.write('Warning: VM SSH credentials not fully set.\r\n');
      }
    };

    socket.onmessage = (event) => {
      const message = event.data;

      try {
        const data = JSON.parse(message);
        if (data.type === 'output' && typeof data.data === 'string') {
          terminal.write(data.data);
          return;
        }
      } catch (error) {
        console.warn('Received non-JSON SSH message, writing raw text.', error);
      }

      if (typeof message === 'string') {
        terminal.write(message);
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
  }, [sshModalOpen, sshModalReady, selectedVm, hasSshDetails]);


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

  const fetchAvailableDevices = async (platformFilter = selectedPlatform) => {
    setLoadingDevices(true);
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

      const normalizedPlatform = platformFilter ? platformFilter.toLowerCase() : null;

      const filteredNodes = normalizedPlatform
        ? nodes.filter((node) => (node?.platform || '').toLowerCase().includes(normalizedPlatform))
        : nodes;

      const normalizeAvailabilitySignal = (value) => {
        if (value === true) return true;
        if (value === false) return false;
        return null;
      };

      const resolveStatusAvailability = (rawStatus) => {
        if (!rawStatus) return null;
        const status = String(rawStatus).toLowerCase();
        if (['online', 'available', 'idle', 'ready'].some((flag) => status.includes(flag))) return true;
        if (['offline', 'busy', 'unavailable', 'error'].some((flag) => status.includes(flag))) return false;
        return null;
      };

      const options = filteredNodes.map((node) => {
        const nodeId = node?.id || node?.deviceName || node?.name;
        const nodeStatus = node?.status;
        const activeSessions = Number(node?.active_sessions ?? node?.activeSessions);
        const maxSessions = Number(node?.max_sessions ?? node?.maxSessions);
        const hasSessionLimits = Number.isFinite(activeSessions) && Number.isFinite(maxSessions);
        const isAvailableFromStatus = resolveStatusAvailability(nodeStatus);
        const isAvailableFromSessions = hasSessionLimits ? activeSessions < maxSessions : null;

        const availabilitySignals = [
          isAvailableFromStatus,
          isAvailableFromSessions
        ].filter((value) => value !== null);

        const hasConflictingSignals = availabilitySignals.includes(true) && availabilitySignals.includes(false);
        const isAvailable =
          availabilitySignals.length > 0
            ? availabilitySignals.some(Boolean)
            : true;

        const derivedStatus = hasConflictingSignals
          ? 'check status'
          : isAvailable
            ? 'available'
            : 'not available';

        const labelParts = [node?.deviceName || nodeId, node?.platform, node?.platform_version]
          .filter(Boolean)
          .join(' • ');

        return {
          value: nodeId,
          label: labelParts || nodeId,
          data: {
            platform: node?.platform || 'Unknown',
            version: node?.platform_version || 'Unknown',
            available: isAvailable,
            status: derivedStatus,
          },
          disabled: !isAvailable,
        };
      });

      setDeviceOptions(options);
    } catch (error) {
      console.error('Failed to fetch devices', error);
      message.error('Failed to load available devices');
      setDeviceOptions([]);
    } finally {
      setLoadingDevices(false);
    }
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

  const emulatorVersionOptions = [10, 11, 12, 13, 14, 15].map((version) => ({
    label: `Android ${version}`,
    value: `Android ${version}`,
  }));

  const filteredVms = vms.filter((vm) => {
    if (!vmSearch.trim()) return true;
    const searchTerm = vmSearch.toLowerCase();
    return [vm.name, vm.platform, vm.version, vm.ip_address]
      .filter(Boolean)
      .some((value) => value.toString().toLowerCase().includes(searchTerm));
  });

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
          {record.status === 'running' && (
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
          <Tooltip title="Open HTTP-based web access for this VM">
            <Button
              size="small"
              icon={<GlobalOutlined />}
              onClick={() => openWebDrawer(record)}
            >
              Web Access
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
              setDeviceType(record.device_type || 'physical');
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

  const cloudColumns = [
    {
      title: 'Server IP',
      dataIndex: 'server_ip',
      key: 'server_ip',
      render: (value) => value || <Typography.Text type="secondary">Not provided</Typography.Text>,
    },
    {
      title: 'Client IP',
      dataIndex: 'client_ip',
      key: 'client_ip',
      render: (value) => value || <Typography.Text type="secondary">Not provided</Typography.Text>,
    },
    {
      title: 'Server DNS',
      dataIndex: 'server_dns',
      key: 'server_dns',
      render: (value) => value || <Typography.Text type="secondary">Not provided</Typography.Text>,
    },
    {
      title: 'Version',
      dataIndex: 'server_version',
      key: 'server_version',
      render: (value, record) =>
        value || record.version || <Typography.Text type="secondary">Auto-detect pending</Typography.Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Run automated tests with Docker execution">
            <Button
              size="small"
              type="primary"
              icon={<ExperimentOutlined />}
              onClick={() => openCloudTestModal(record)}
              style={{ background: '#52c41a', borderColor: '#52c41a' }}
            >
              Start
            </Button>
          </Tooltip>
          <Popconfirm
            title="Remove cloud service"
            description="This will remove the cloud service from the testbed."
            okType="danger"
            onConfirm={() => removeCloudService(record.id)}
          >
            <Button danger size="small">Delete</Button>
          </Popconfirm>
        </Space>
      ),
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

  return (
    <div>
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography.Title level={3} style={{ margin: 0 }}>
              Testbed
            </Typography.Title>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={refreshTestbed}
                loading={refreshingTestbed || loading}
              >
                Refresh
              </Button>
              <Dropdown
                menu={{
                  items: [
                    { key: 'vm', label: 'Virtual Machine' },
                    { key: 'cloud', label: 'Cloud Service' },
                  ],
                  onClick: handleAddNewSelection,
                }}
                placement="bottomRight"
                trigger={['click']}
              >
                <Button type="primary" icon={<PlusOutlined />}>
                  Add New
                </Button>
              </Dropdown>
            </Space>
          </div>
        }
        bodyStyle={{ paddingTop: 12 }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography.Title level={4} style={{ margin: 0 }}>VMs</Typography.Title>
          </div>
          <Input.Search
            placeholder="Search VMs"
            allowClear
            onChange={(e) => setVmSearch(e.target.value)}
            style={{ maxWidth: 300 }}
            value={vmSearch}
          />
          <Table
            dataSource={filteredVms}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 5 }}
            style={{ marginTop: 12 }}
          />

          <Divider style={{ margin: '12px 0' }} />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography.Title level={4} style={{ margin: 0 }}>Cloud Services</Typography.Title>
          </div>
          <Table
            dataSource={cloudServices}
            columns={cloudColumns}
            rowKey="id"
            pagination={false}
            size="small"
            locale={{ emptyText: <Empty description="No cloud services configured" /> }}
          />

          <Divider style={{ margin: '12px 0' }} />
        </Space>
      </Card>

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
          <Form.Item label="Web Access URL" name="web_url" tooltip="Optional HTTP/HTTPS URL for the VM's management UI">
            <Input placeholder="e.g. https://10.0.0.5" />
          </Form.Item>
          <Form.Item label="Web Username" name="web_username">
            <Input placeholder="Optional username hint for the web UI" />
          </Form.Item>
          <Form.Item label="Web Password" name="web_password">
            <Input.Password placeholder="Optional password hint for the web UI" />
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
        title="Add Cloud Service"
        open={cloudModalOpen}
        onCancel={() => setCloudModalOpen(false)}
        onOk={handleSaveCloudService}
        okText="Save"
        confirmLoading={fetchingCloudVersion}
      >
        <Form form={cloudForm} layout="vertical">
          <Form.Item
            label="Server IP"
            name="server_ip"
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (value || getFieldValue('server_dns')) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Please enter a server IP or DNS'));
                },
              }),
            ]}
          >
            <Input placeholder="10.0.0.12" />
          </Form.Item>

          <Form.Item
            label="Client IP"
            name="client_ip"
            rules={[{ required: true, message: 'Please enter the client IP' }]}
          >
            <Input placeholder="10.0.0.10" />
          </Form.Item>

          <Form.Item
            label="Server DNS"
            name="server_dns"
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (value || getFieldValue('server_ip')) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Please enter a server IP or DNS'));
                },
              }),
            ]}
          >
            <Input placeholder="gateway.example.com" />
          </Form.Item>

          <Form.Item
            label="Server Version (optional)"
            name="server_version"
            tooltip="We will try to detect this automatically when possible."
          >
            <Input
              placeholder="Auto-detected"
              addonAfter={(
                <Button type="link" onClick={detectCloudVersion} loading={fetchingCloudVersion} style={{ padding: 0 }}>
                  Auto-detect
                </Button>
              )}
            />
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
          setSshModalReady(false);
        }}
        afterOpenChange={(open) => setSshModalReady(open)}
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

      <Drawer
        title={`Web Access - ${selectedVm?.name || ''}`}
        placement="right"
        width={900}
        onClose={() => {
          setWebDrawerOpen(false);
          setSelectedVm(null);
          setWebAccessUrl('');
          setWebEmbedAllowed(true);
          setWebLoadError(null);
        }}
        open={webDrawerOpen}
        extra={
          webAccessUrl ? (
            <Button
              type="primary"
              size="small"
              onClick={() => window.open(webAccessUrl, '_blank', 'noopener,noreferrer')}
            >
              Open in New Tab
            </Button>
          ) : null
        }
      >
        {!webAccessUrl ? (
          <Empty description="No web access URL configured" />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Typography.Text type="secondary">{webAccessUrl}</Typography.Text>
            {(selectedVm?.web_username || selectedVm?.web_password) && (
              <Alert
                type="info"
                showIcon
                message="Credentials hint"
                description={
                  <div>
                    {selectedVm?.web_username && (
                      <div>
                        <strong>Username:</strong> {selectedVm.web_username}
                      </div>
                    )}
                    {selectedVm?.web_password && (
                      <div>
                        <strong>Password:</strong> {selectedVm.web_password}
                      </div>
                    )}
                  </div>
                }
              />
            )}
            {!webEmbedAllowed && (
              <Alert
                type="warning"
                showIcon
                message="Embedded preview disabled"
                description="The target site blocks iframe embedding. Use the 'Open in New Tab' button to access it."
              />
            )}
            {webEmbedAllowed && (
              <div style={{ height: 600, border: '1px solid #f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
                <iframe
                  title="VM Web Access"
                  src={webAccessUrl}
                  style={{ width: '100%', height: '100%', border: 'none' }}
                  onLoad={() => setWebLoadError(null)}
                  onError={() =>
                    setWebLoadError('Unable to load the web access page. Check the URL or frame permissions.')
                  }
                />
              </div>
            )}
            {webLoadError && <Alert type="error" showIcon message={webLoadError} />}
          </Space>
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
                    fetchAvailableDevices(value);
                    const updates = { apk_id: undefined, device_id: undefined, emulator_version: undefined };
                    if (value === 'ios') {
                      setDeviceType('physical');
                      updates.device_type = 'physical';
                    }
                    testForm.setFieldsValue(updates);
                  }}
                  options={[
                    { label: 'iOS', value: 'ios' },
                    { label: 'Android', value: 'android' }
                  ]}
                />
              </Form.Item>

              <Form.Item
                name="device_type"
                label="Device Type"
                rules={[{ required: true, message: 'Please select a device type' }]}
              >
                <Radio.Group
                  value={deviceType}
                  onChange={(e) => {
                    const value = e.target.value;
                    setDeviceType(value);
                    testForm.setFieldsValue({ device_id: undefined, emulator_version: undefined, device_type: value });
                  }}
                >
                  <Radio value="physical">Physical Device</Radio>
                  <Radio value="emulator" disabled={selectedPlatform === 'ios'}>
                    Android Emulator
                  </Radio>
                </Radio.Group>
              </Form.Item>

              {deviceType === 'physical' ? (
                <Form.Item
                  name="device_id"
                  label="Physical Device"
                  rules={[
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (getFieldValue('device_type') !== 'physical') {
                          return Promise.resolve();
                        }
                        if (value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('Please select a physical device'));
                      },
                    }),
                  ]}
                  tooltip="Devices and availability mirror the Devices page"
                >
                  <Select
                    placeholder="Select an available device"
                    loading={loadingDevices}
                    optionFilterProp="label"
                    options={deviceOptions}
                    notFoundContent={loadingDevices ? 'Loading devices...' : 'No devices found'}
                    optionRender={(option) => {
                      const data = option.data.data;
                      const statusLabel = data?.status || (data?.available ? 'available' : 'not available');
                      const statusColor = statusLabel === 'check status' ? 'orange' : data?.available ? 'green' : 'red';
                      return (
                        <Space>
                          <span>{option.label}</span>
                          {data?.platform && <Tag>{data.platform}</Tag>}
                          {data?.version && <Tag color="blue">{data.version}</Tag>}
                          <Tag color={statusColor}>{statusLabel?.toUpperCase()}</Tag>
                        </Space>
                      );
                    }}
                  />
                </Form.Item>
              ) : (
                <Form.Item
                  name="emulator_version"
                  label="Android Emulator Version"
                  rules={[
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (getFieldValue('device_type') !== 'emulator') {
                          return Promise.resolve();
                        }
                        if (value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('Please select an emulator Android version'));
                      },
                    }),
                  ]}
                  tooltip="Select the Android version to emulate (10 - 15)"
                >
                  <Select placeholder="Choose Android version" options={emulatorVersionOptions} />
                </Form.Item>
              )}

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
