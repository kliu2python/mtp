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
  Upload,
  message
} from 'antd';
import {
  CodeOutlined,
  DeleteOutlined,
  ExperimentOutlined,
  GlobalOutlined,
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { API_URL, JENKINS_CLOUD_API_URL } from '../constants';

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
  const [facTestModalOpen, setFacTestModalOpen] = useState(false);
  const [selectedFacVm, setSelectedFacVm] = useState(null);
  const [facTestResults, setFacTestResults] = useState({});
  const [quickGuideModalOpen, setQuickGuideModalOpen] = useState(false);
  const [vmSearch, setVmSearch] = useState('');
  const [testTemplates, setTestTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [deviceType, setDeviceType] = useState('physical');
  const [deviceOptions, setDeviceOptions] = useState([]);
  const [loadingDevices, setLoadingDevices] = useState(false);
  const [cloudServices, setCloudServices] = useState([]);
  const [cloudModalOpen, setCloudModalOpen] = useState(false);
  const [fetchingCloudVersion, setFetchingCloudVersion] = useState(false);
  const [cloudLoading, setCloudLoading] = useState(false);
  const [savingCloudService, setSavingCloudService] = useState(false);
  const [refreshingTestbed, setRefreshingTestbed] = useState(false);
  const [appUploadLoading, setAppUploadLoading] = useState(false);
  const [updateCloudModalOpen, setUpdateCloudModalOpen] = useState(false);
  const [updatingCloudService, setUpdatingCloudService] = useState(false);
  const [editingCloudService, setEditingCloudService] = useState(null);
  const [updateCloudForm] = Form.useForm();

  // Cloud service info cache
  const [cloudServiceInfoCache, setCloudServiceInfoCache] = useState({});

  // Run Previous states
  const [runPreviousModalOpen, setRunPreviousModalOpen] = useState(false);
  const [previousTestConfig, setPreviousTestConfig] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loadingPreviousConfig, setLoadingPreviousConfig] = useState(false);

  const resolveTestingProductOptions = (testbedPlatform) => {
    if (testbedPlatform === 'FortiGate') {
      return [
        { label: 'FortiGate', value: 'FortiGate' },
        { label: 'FortiTokenCloud_FGT', value: 'FortiTokenCloud_FGT' },
      ];
    }

    if (testbedPlatform === 'FortiAuthenticator') {
      return [
        { label: 'FortiAuthenticator', value: 'FortiAuthenticator' },
        { label: 'FortiTokenCloud_FGT', value: 'FortiTokenCloud_FGT' },
      ];
    }

    return [
      { label: 'FortiTokenCloud_FGT', value: 'FortiTokenCloud_FGT' },
    ];
  };

  useEffect(() => {
    fetchVMs();
    fetchCloudServices();
    refreshTestbed();
  }, []);

  const fetchVMs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/vms`);
      const vmsData = response.data.vms;

      // Fetch FAC test timestamps for all FortiAuthenticator VMs
      const vmsWithTimestamps = await Promise.all(vmsData.map(async (vm) => {
        if (vm.platform === 'FortiAuthenticator') {
          try {
            const timestampResponse = await axios.get(`${API_URL}/api/vms/${vm.id}/fac-test-timestamp`);
            return {
              ...vm,
              fac_last_test_timestamp: timestampResponse.data.timestamp
            };
          } catch (error) {
            // If we can't fetch the timestamp, return the VM as is
            return vm;
          }
        }
        return vm;
      }));

      setVms(vmsWithTimestamps);
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

          // Update the service in the database
          try {
            await axios.put(`${API_URL}/api/cloud/services/${service.id}`, {
              server_version: latestVersion,
            });
          } catch (updateError) {
            console.error(`Failed to update cloud service ${service.id}:`, updateError);
            // Continue anyway, we'll still update the UI
          }

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

  const handleAppFileUpload = async ({ file, onSuccess, onError }) => {
    if (!selectedPlatform) {
      message.warning('Please select a platform before uploading an app file.');
      onError?.();
      return;
    }

    const formData = new FormData();
    formData.append('files', file);

    setAppUploadLoading(true);
    try {
      await axios.post(`${API_URL}/api/files/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      message.success('App file uploaded successfully');
      await fetchApksForPlatform(selectedPlatform);
      testForm.setFieldsValue({ apk_id: file.name });
      onSuccess?.();
    } catch (error) {
      message.error('Failed to upload app file');
      onError?.(error);
    } finally {
      setAppUploadLoading(false);
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
    const testingProductOptions = resolveTestingProductOptions(vm.platform);
    const defaultTestingProduct = testingProductOptions[0]?.value;
    setSelectedPlatform(defaultPlatform);
    testForm.setFieldsValue({
      platform: defaultPlatform,
      test_scope: 'functional',
      environment: 'qa',
      timeout: 3600,
      device_type: 'physical',
      test_product: defaultTestingProduct,
    });
    // Fetch APKs for the default platform
    fetchApksForPlatform(defaultPlatform);
    fetchAvailableDevices(defaultPlatform);
    setTestModalOpen(true);
  };

  const openFacTestModal = async (vm) => {
    setSelectedFacVm(vm);
    setFacTestModalOpen(true);
    // Reset test results when opening modal
    setFacTestResults({});

    // Fetch the last FAC test timestamp
    try {
      const response = await axios.get(`${API_URL}/api/vms/${vm.id}/fac-test-timestamp`);
      if (response.data.timestamp) {
        // Store the timestamp in the component state
        setFacTestResults(prev => ({
          ...prev,
          lastTestTimestamp: response.data.timestamp
        }));
      }
    } catch (error) {
      // Silently ignore errors fetching timestamp
      console.debug('Could not fetch FAC test timestamp:', error);
    }
  };

  const testFacConnectivity = async (vmId) => {
    // Update state to show loading
    setFacTestResults(prev => ({
      ...prev,
      connectivity: { loading: true }
    }));

    try {
      const response = await axios.post(`${API_URL}/api/vms/${vmId}/test-fac-connectivity`);
      const timestamp = new Date().toISOString();

      if (response.data.success) {
        message.success(response.data.message);
        // Update state with success result and timestamp
        setFacTestResults(prev => ({
          ...prev,
          connectivity: {
            success: true,
            message: response.data.message,
            timestamp: timestamp,
            loading: false
          },
          lastTestTimestamp: timestamp
        }));
      } else {
        message.error(response.data.message);
        // Update state with error result and timestamp
        setFacTestResults(prev => ({
          ...prev,
          connectivity: {
            success: false,
            message: response.data.message,
            timestamp: timestamp,
            loading: false
          }
        }));
      }
    } catch (error) {
      const timestamp = new Date().toISOString();
      const errorMessage = error.response?.data?.detail || 'Failed to test FortiAuthenticator connectivity';
      message.error(errorMessage);
      // Update state with error result and timestamp
      setFacTestResults(prev => ({
        ...prev,
        connectivity: {
          success: false,
          message: errorMessage,
          timestamp: timestamp,
          loading: false
        }
      }));
    }
  };

  const testFacUserCreation = async (vmId) => {
    // Update state to show loading
    setFacTestResults(prev => ({
      ...prev,
      userCreation: { loading: true }
    }));

    try {
      const response = await axios.post(`${API_URL}/api/vms/${vmId}/test-fac-user-creation`);
      const timestamp = new Date().toISOString();

      if (response.data.ftm_user_creation.success && response.data.ftc_user_creation.success) {
        message.success('Both FTK and FTC user creation tests passed');
        // Update state with success result and timestamp
        setFacTestResults(prev => ({
          ...prev,
          userCreation: {
            success: true,
            ftkMessage: response.data.ftm_user_creation.message,
            ftcMessage: response.data.ftc_user_creation.message,
            timestamp: timestamp,
            loading: false
          },
          lastTestTimestamp: timestamp
        }));
      } else {
        const ftmMessage = response.data.ftm_user_creation.message;
        const ftcMessage = response.data.ftc_user_creation.message;
        message.error(`FTK: ${ftmMessage}, FTC: ${ftcMessage}`);
        // Update state with error result and timestamp
        setFacTestResults(prev => ({
          ...prev,
          userCreation: {
            success: false,
            ftkMessage: ftmMessage,
            ftcMessage: ftcMessage,
            timestamp: timestamp,
            loading: false
          }
        }));
      }
    } catch (error) {
      const timestamp = new Date().toISOString();
      const errorMessage = error.response?.data?.detail || 'Failed to test FortiAuthenticator user creation';
      message.error(errorMessage);
      // Update state with error result and timestamp
      setFacTestResults(prev => ({
        ...prev,
        userCreation: {
          success: false,
          ftkMessage: errorMessage,
          ftcMessage: errorMessage,
          timestamp: timestamp,
          loading: false
        }
      }));
    }
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
        const validationFields = ['test_scope', 'environment', 'test_product'];
        if (testForm.getFieldValue('environment') === 'custom') {
          validationFields.push('custom_environment');
        }
        await testForm.validateFields(validationFields);
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

      const environmentValue =
        values.environment === 'custom' ? values.custom_environment : values.environment;

      const selectedTestSuite = values.test_product;

      const parameters = Object.fromEntries(
        Object.entries({
          platform: values.platform,
          test_scope: values.test_scope,
          test_suite: selectedTestSuite,
          timeout: values.timeout,
          device_type: values.device_type,
          device_id: values.device_type === 'physical' ? values.device_id : undefined,
          emulator_version: values.device_type === 'emulator' ? values.emulator_version : undefined,
          apk_id: appSourceType === 'file' ? values.apk_id : undefined,
          app_version: appSourceType === 'version' ? values.app_version : undefined,
          test_product: values.test_product,
          vm_ip: selectedTestVm?.ip_address,
          vm_name: selectedTestVm?.name,
        }).filter(([, value]) => value !== undefined && value !== null && value !== '')
      );

      const normalizedEnvironment =
        typeof environmentValue === 'string'
          ? environmentValue
          : environmentValue;

      const payload = {
        environment: normalizedEnvironment,
        platforms: [values.platform],
        parameters,
        custom: {
          save_as_template: values.save_as_template || false,
          template_name: values.save_as_template ? values.template_name : undefined,
        },
        project: values.platform === 'ios' ? 'ftm_ios' : 'ftm_android',
      };

      const response = await axios.post(
        `${JENKINS_CLOUD_API_URL}/run/execute/ftm`,
        payload
      );

      if (response.data?.results) {
        message.success('FTM test execution submitted to Jenkins Cloud');
        setTestModalOpen(false);
        testForm.resetFields();
      } else {
        message.warning('Request sent but no confirmation returned from Jenkins Cloud');
      }
    } catch (error) {
      console.error('Failed to start test:', error);
      const errorMsg = error?.response?.data?.error || error?.response?.data?.detail || 'Failed to start auto test';
      message.error(errorMsg);
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

  const openTemplatesModal = async (vm) => {
    setSelectedTestVm(vm);
    setLoadingPreviousConfig(true);
    setRunPreviousModalOpen(true);

    try {
      const response = await axios.get(`${API_URL}/api/tests/templates`);
      setPreviousTestConfig(response.data);
    } catch (error) {
      message.error(error?.response?.data?.detail || 'No test templates found');
      setRunPreviousModalOpen(false);
    } finally {
      setLoadingPreviousConfig(false);
    }
  };

  const runTemplateTest = async () => {
    try {
      setStartingTest(true);

      // Use the selected template to run the test
      const response = await axios.post(
        `${JENKINS_CLOUD_API_URL}/tests/run-template`,
        {
          template_id: selectedTemplate?.id || previousTestConfig?.id,
          vm_id: selectedTestVm.id
        }
      );

      if (response.data?.results) {
        message.success('FTM test execution submitted to Jenkins Cloud');

        setRunPreviousModalOpen(false);
        setPreviousTestConfig(null);
        setSelectedTemplate(null);
      } else {
        message.warning('Request sent but no confirmation returned from Jenkins Cloud');
      }
    } catch (error) {
      console.error('Failed to run test from template:', error);
      message.error(error?.response?.data?.detail || 'Failed to run test from template');
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
      ip_address: vm.ip_address,
      ssh_username: vm.ssh_username,
      ssh_password: vm.ssh_password,
      api_key: vm.api_key,
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
      setSavingCloudService(true);
      const { data } = await axios.post(`${API_URL}/api/cloud/services`, values);
      const createdService = data?.cloud_service;

      if (createdService) {
        setCloudServices((prev) => [...prev, createdService]);
      }

      setCloudModalOpen(false);
      message.success('Cloud service added');
    } catch (error) {
      if (error.errorFields) return;
      const detail = error.response?.data?.detail;
      message.error(detail || 'Failed to save cloud service');
    } finally {
      setSavingCloudService(false);
    }
  };

  const fetchCloudServices = async () => {
    try {
      setCloudLoading(true);
      const { data } = await axios.get(`${API_URL}/api/cloud/services`);
      setCloudServices(data?.cloud_services || []);
    } catch (error) {
      message.error('Failed to load cloud services');
    } finally {
      setCloudLoading(false);
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

  const removeCloudService = async (serviceId) => {
    try {
      await axios.delete(`${API_URL}/api/cloud/services/${serviceId}`);
      setCloudServices((prev) => prev.filter((service) => service.id !== serviceId));
      message.success('Cloud service removed');
    } catch (error) {
      message.error('Failed to remove cloud service');
    }
  };

  const checkCloudInfo = async (service) => {
    // Check if we have cached information for this service
    const cacheKey = service.id;
    const cachedInfo = cloudServiceInfoCache[cacheKey];

    // If we have cached info, show it immediately
    if (cachedInfo) {
      Modal.success({
        title: 'Cloud Service Information (Cached)',
        content: (
          <div>
            <p><strong>Token Format:</strong> {cachedInfo.tokenFormat}</p>
            <p><strong>Sandbox Status:</strong> {cachedInfo.sandboxStatus}</p>
            <p>All configuration files are consistent.</p>
            <p style={{ fontSize: '0.9em', color: '#888' }}>
              Last updated: {new Date(cachedInfo.timestamp).toLocaleString()}
            </p>
          </div>
        ),
        width: 500,
      });
      return;
    }

    let sessionId = null;
    let loadingModal;

    try {
      // Show loading modal
      loadingModal = Modal.info({
        title: 'Checking Cloud Service Info',
        content: 'Please wait while we check the cloud service configuration...',
        icon: null,
        okText: 'Cancel',
        onOk: () => {},
        closable: true,
      });

      // Step 1: Login to FortiToken Cloud Ops service
      const loginPayload = {
        "jumpbox_host": "10.160.41.4",
        "jumpbox_user": "labuser",
        "jumpbox_password": "fortinet",
        "target_host": service.server_ip || "10.160.83.46",
        "target_user": "cloud-user",
        "target_key_file": "id_rsa_jenkins"
      };

      const loginResponse = await axios.post(`${API_URL}/api/cloud/fic/auth/login`, loginPayload);
      sessionId = loginResponse.data.session_id;

      // Step 2: Set up authorization header for subsequent requests
      const authHeader = { Authorization: `Bearer ${sessionId}` };

      // Step 3: Fetch token format version
      const tokenFormatResponse = await axios.get(`${API_URL}/api/cloud/fic/token-format`, {
        headers: authHeader
      });

      // Step 4: Fetch sandbox status
      const sandboxResponse = await axios.get(`${API_URL}/api/cloud/fic/push/sandbox`, {
        headers: authHeader
      });

      // Close loading modal
      loadingModal.destroy();

      // Step 5: Validate responses and display information
      // Handle token format response (could be array or single object)
      let tokenFormatData = tokenFormatResponse.data;
      if (!Array.isArray(tokenFormatData)) {
        tokenFormatData = [tokenFormatData];
      }

      // Handle sandbox response (could be array or single object)
      let sandboxData = sandboxResponse.data;
      if (!Array.isArray(sandboxData)) {
        sandboxData = [sandboxData];
      }

      // Validate that all files have the same token_format_version
      const tokenFormats = tokenFormatData.map(item => item.token_format_version).filter(Boolean);
      const uniqueTokenFormats = [...new Set(tokenFormats)];

      // Validate that all files have the same use_sandbox value
      const sandboxValues = sandboxData.map(item => item.use_sandbox).filter(Boolean);
      const uniqueSandboxValues = [...new Set(sandboxValues)];

      // Check for errors
      const hasTokenFormatError = uniqueTokenFormats.length !== 1;
      const hasSandboxError = uniqueSandboxValues.length !== 1;

      if (hasTokenFormatError || hasSandboxError) {
        let errorMessage = 'Configuration mismatch detected:\n';
        if (hasTokenFormatError) {
          errorMessage += `• Token formats differ across files (${tokenFormats.join(', ')}).\n`;
        }
        if (hasSandboxError) {
          errorMessage += `• Sandbox settings differ across files (${sandboxValues.join(', ')}).\n`;
        }

        Modal.error({
          title: 'Cloud Service Configuration Error',
          content: (
            <div style={{ whiteSpace: 'pre-wrap' }}>
              {errorMessage}
              <p>Please check your cloud service configuration.</p>
            </div>
          ),
          width: 600,
        });
      } else {
        // All values are consistent, display the information
        const tokenFormat = uniqueTokenFormats[0] || 'N/A';
        const sandboxStatus = uniqueSandboxValues[0] || 'N/A';

        // Update cache with new information
        setCloudServiceInfoCache(prevCache => ({
          ...prevCache,
          [cacheKey]: {
            tokenFormat,
            sandboxStatus,
            timestamp: Date.now()
          }
        }));

        Modal.success({
          title: 'Cloud Service Information',
          content: (
            <div>
              <p><strong>Token Format:</strong> {tokenFormat}</p>
              <p><strong>Sandbox Status:</strong> {sandboxStatus}</p>
              <p>All configuration files are consistent.</p>
            </div>
          ),
          width: 500,
        });
      }
    } catch (error) {
      console.error('Error checking cloud info:', error);

      // Close loading modal if it exists
      if (loadingModal) {
        loadingModal.destroy();
      }

      Modal.error({
        title: 'Failed to Check Cloud Service Info',
        content: (
          <div>
            <p>An error occurred while checking the cloud service information:</p>
            <p style={{ color: 'red' }}>{error.message || 'Unknown error'}</p>
            <p>Please try again later.</p>
          </div>
        ),
        width: 500,
      });
    } finally {
      // Step 6: Logout if we have a session
      if (sessionId) {
        try {
          await axios.post(`${API_URL}/api/cloud/fic/auth/logout`, {}, {
            headers: { Authorization: `Bearer ${sessionId}` }
          });
        } catch (logoutError) {
          // Ignore logout errors
        }
      }
    }
  };

  const updateCloudInfo = async (service) => {
    // Open the update info modal
    setEditingCloudService(service);
    setUpdateCloudModalOpen(true);
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

  const normalizeWebUrl = (url, platform) => {
    try {
      const parsed = new URL(url);
      // Use HTTPS for FortiAuthenticator, HTTP for FortiGate and others
      if (platform === 'FortiAuthenticator') {
        parsed.protocol = 'https:';
      } else {
        parsed.protocol = 'http:';
      }
      return parsed.toString();
    } catch (error) {
      // If the URL constructor fails, fall back to the raw value.
      return url;
    }
  };

  const openWebDrawer = (vm) => {
    const baseUrl = vm.web_url || (vm.ip_address ? `http://${vm.ip_address}` : null);
    const resolvedUrl = baseUrl ? normalizeWebUrl(baseUrl, vm.platform) : null;
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
      // Fetch devices from the new stream endpoint
      const response = await axios.get(`${API_URL}/api/devices/stream/list`);

      const { devices: devicesData } = response.data;

      const normalizedPlatform = platformFilter ? platformFilter.toLowerCase() : null;

      const filteredDevices = normalizedPlatform
        ? devicesData.filter((device) => (device?.platform || '').toLowerCase().includes(normalizedPlatform))
        : devicesData;

      const options = filteredDevices.map((device) => {
        const deviceId = device?.id || device?.name;
        const isAvailable = device?.status === 'available';

        const labelParts = [device?.name || deviceId, device?.platform, device?.os_version]
          .filter(Boolean)
          .join(' • ');

        return {
          value: deviceId,
          label: labelParts || deviceId,
          data: {
            platform: device?.platform || 'Unknown',
            version: device?.os_version || 'Unknown',
            available: isAvailable,
            status: device?.status || 'unknown',
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

  const testingProductOptions = resolveTestingProductOptions(selectedTestVm?.platform);
  const uploadAccept = selectedPlatform === 'ios' ? '.ipa' : selectedPlatform === 'android' ? '.apk' : '.apk,.ipa';

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
          <Tooltip title="Select and run test from saved templates">
            <Button
              size="small"
              type="default"
              icon={<ReloadOutlined />}
              onClick={() => openTemplatesModal(record)}
            >
              Templates
            </Button>
          </Tooltip>
          {record.platform === 'FortiAuthenticator' && (
            <Tooltip title="Test FortiAuthenticator">
              <Button
                size="small"
                type="default"
                onClick={() => openFacTestModal(record)}
              >
                Test FAC
              </Button>
            </Tooltip>
          )}
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
      title: 'Testing Product',
      dataIndex: 'test_product',
      key: 'test_product',
      render: (value, record) => value || record.test_suite || 'N/A',
    },
    {
      title: 'Environment',
      dataIndex: 'environment',
      key: 'environment',
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
              const templateOptions = resolveTestingProductOptions(selectedTestVm?.platform || record.platform);
              const templateProduct = record.test_product || record.test_suite;
              const normalizedProduct =
                templateOptions.find((option) => option.value === templateProduct)?.value
                || templateOptions[0]?.value;

              testForm.setFieldsValue({
                ...record,
                test_product: normalizedProduct,
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
          <Tooltip title="Check cloud service information">
            <Button
              size="small"
              icon={<GlobalOutlined />}
              onClick={() => checkCloudInfo(record)}
            >
              Check Info
            </Button>
          </Tooltip>
          <Tooltip title="Update cloud service information">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => updateCloudInfo(record)}
            >
              Update Info
            </Button>
          </Tooltip>
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
              <Button onClick={() => setQuickGuideModalOpen(true)}>
                Quick Guide
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
            <Typography.Title level={4} style={{ margin: 0, fontSize: '16px' }}>VMs</Typography.Title>
            <Input.Search
              placeholder="Search VMs"
              allowClear
              onChange={(e) => setVmSearch(e.target.value)}
              style={{ maxWidth: 300, fontSize: '12px' }}
              value={vmSearch}
              size="small"
            />
          </div>
          <Table
            dataSource={filteredVms}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 4 }}
            style={{ marginTop: 12 }}
          />

          <Divider style={{ margin: '12px 0' }} />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography.Title level={4} style={{ margin: 0, fontSize: '16px' }}>Cloud Services</Typography.Title>
          </div>
          <Table
            dataSource={cloudServices}
            columns={cloudColumns}
            rowKey="id"
            loading={cloudLoading}
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
              onChange={(value) => {
                // Trigger a re-render to show/hide conditional fields
                form.setFieldsValue({ platform: value });
              }}
            />
          </Form.Item>
          <Form.Item
            label="Version"
            name="version"
            rules={[{ required: true, message: 'Please input version' }]}
          >
            <Input />
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
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, curValues) => prevValues.platform !== curValues.platform}
          >
            {({ getFieldValue }) =>
              getFieldValue('platform') === 'FortiAuthenticator' ? (
                <Form.Item
                  label="API Key"
                  name="api_key"
                  tooltip="API key for FortiAuthenticator access"
                >
                  <Input placeholder="Enter API key for FortiAuthenticator" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Add Cloud Service"
        open={cloudModalOpen}
        onCancel={() => setCloudModalOpen(false)}
        onOk={handleSaveCloudService}
        okText="Save"
        confirmLoading={savingCloudService}
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
                  tooltip="Select a specific app version from uploaded files or upload a new one"
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
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

                    <Upload
                      customRequest={handleAppFileUpload}
                      showUploadList={false}
                      disabled={!selectedPlatform || appUploadLoading || appSourceType !== 'file'}
                      accept={uploadAccept}
                    >
                      <Button
                        icon={<UploadOutlined />}
                        loading={appUploadLoading}
                        disabled={!selectedPlatform || appUploadLoading}
                      >
                        Upload new {selectedPlatform === 'ios' ? 'IPA' : 'APK'}
                      </Button>
                    </Upload>
                    {!selectedPlatform && (
                      <Typography.Text type="secondary">
                        Select a platform to enable uploading a new app file.
                      </Typography.Text>
                    )}
                  </Space>
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
                name="environment"
                label="Test Environment"
                rules={[{ required: true, message: 'Please select environment' }]}
                tooltip="Select where this test will run"
              >
                <Radio.Group>
                  <Radio value="prod">Prod</Radio>
                  <Radio value="qa">QA</Radio>
                  <Radio value="custom">Custom</Radio>
                </Radio.Group>
              </Form.Item>

              {testForm.getFieldValue('environment') === 'custom' && (
                <Form.Item
                  name="custom_environment"
                  label="Custom Environment"
                  rules={[{ required: true, message: 'Please enter custom environment' }]}
                  tooltip="Provide the exact environment identifier when using a custom target"
                >
                  <Input placeholder="e.g., staging-us-west" />
                </Form.Item>
              )}

              <Form.Item
                name="test_scope"
                label="Test Scope"
                rules={[{ required: true, message: 'Please select test scope' }]}
                tooltip="Select the test scope to run"
              >
                <Select
                  placeholder="Select test scope"
                  options={[
                    { label: 'Functional Test (more test cases)', value: 'functional' },
                    { label: 'Integration Test', value: 'integration' },
                    { label: 'Regression Test', value: 'regression' },
                    { label: 'Acceptable Test (less test cases)', value: 'acceptable' }
                  ]}
                />
              </Form.Item>

              <Form.Item
                name="test_product"
                label="Testing Product (Test Suite)"
                rules={[{ required: true, message: 'Please select testing product' }]}
                tooltip="Select the product under test. The selected product will be used as the test suite."
              >
                <Select
                  placeholder="Select testing product"
                  options={testingProductOptions}
                />
              </Form.Item>
            </>
          )}

          {currentStep === 2 && (
            <>
              <Alert
                type="info"
                message="Step 3: Execution Settings"
                description="Configure timeout and template preferences. Docker image details are now managed by the test environment."
                showIcon
                style={{ marginBottom: 16 }}
              />

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
        title={`Select Test Template${selectedTestVm ? ` - ${selectedTestVm.name}` : ''}`}
        open={runPreviousModalOpen}
        onCancel={() => {
          setRunPreviousModalOpen(false);
          setPreviousTestConfig(null);
          setSelectedTemplate(null);
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setRunPreviousModalOpen(false);
            setPreviousTestConfig(null);
            setSelectedTemplate(null);
          }}>
            Cancel
          </Button>,
          <Button key="run" type="primary" onClick={runTemplateTest} loading={startingTest}>
            Run Test
          </Button>
        ]}
        width={700}
      >
        {loadingPreviousConfig ? (
          <Spin />
        ) : previousTestConfig ? (
          <>
            <Card size="small" title="Available Test Templates" style={{ marginBottom: 16 }}>
              {Array.isArray(previousTestConfig) && previousTestConfig.length > 0 ? (
                <Table
                  dataSource={previousTestConfig}
                  columns={[
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
                      title: 'Environment',
                      dataIndex: 'environment',
                      key: 'environment',
                    },
                    {
                      title: 'Action',
                      key: 'action',
                      render: (_, record) => (
                        <Button
                          type="primary"
                          size="small"
                          onClick={() => {
                            setSelectedTemplate(record);
                            setPreviousTestConfig(record);
                            runTemplateTest();
                          }}
                        >
                          Use Template
                        </Button>
                      ),
                    },
                  ]}
                  rowKey="id"
                  pagination={false}
                />
              ) : (
                <Empty description="No test templates available" />
              )}
            </Card>

            <Alert
              type="info"
              message="Select a template to run tests"
              description="Choose from saved test configurations to quickly run tests with predefined settings."
              showIcon
            />
          </>
        ) : (
          <Empty description="No test templates available" />
        )}
      </Modal>

      <Modal
        title="Update Cloud Service Information"
        open={updateCloudModalOpen}
        onCancel={() => {
          setUpdateCloudModalOpen(false);
          updateCloudForm.resetFields();
          setEditingCloudService(null);
        }}
        onOk={async () => {
          let sessionId = null;

          try {
            const values = await updateCloudForm.validateFields();
            setUpdatingCloudService(true);

            // Step 1: Login to FortiToken Cloud Ops service
            const loginPayload = {
              "jumpbox_host": "10.160.41.4",
              "jumpbox_user": "labuser",
              "jumpbox_password": "fortinet",
              "target_host": editingCloudService?.server_ip || "10.160.83.46",
              "target_user": "cloud-user",
              "target_key_file": "id_rsa_jenkins"
            };

            const loginResponse = await axios.post(`${API_URL}/api/cloud/fic/auth/login`, loginPayload);
            sessionId = loginResponse.data.session_id;

            // Step 2: Set up authorization header for subsequent requests
            const authHeader = { Authorization: `Bearer ${sessionId}` };

            // Step 3: Update token format version if provided
            if (values.token_format_version) {
              await axios.put(`${API_URL}/api/cloud/fic/token-format`,
                { format: values.token_format_version },
                { headers: authHeader }
              );
            }

            // Step 4: Update sandbox mode if provided
            if (values.use_sandbox) {
              await axios.put(`${API_URL}/api/cloud/fic/push/sandbox`,
                { value: values.use_sandbox },
                { headers: authHeader }
              );
            }

            // Update the cloud service information in the UI
            const updatedServices = cloudServices.map(service =>
              service.id === editingCloudService?.id
                ? { ...service, ...values }
                : service
            );

            setCloudServices(updatedServices);

            // Clear cache for this service after successful update
            const cacheKey = editingCloudService?.id;
            if (cacheKey) {
              setCloudServiceInfoCache(prevCache => {
                const newCache = { ...prevCache };
                delete newCache[cacheKey];
                return newCache;
              });
            }

            setUpdateCloudModalOpen(false);
            updateCloudForm.resetFields();
            setEditingCloudService(null);
            message.success('Cloud service information updated successfully');
          } catch (error) {
            console.error('Error updating cloud service:', error);
            message.error('Failed to update cloud service information');
          } finally {
            setUpdatingCloudService(false);
            // Step 5: Logout if we have a session
            if (sessionId) {
              try {
                await axios.post(`${API_URL}/api/cloud/fic/auth/logout`, {}, {
                  headers: { Authorization: `Bearer ${sessionId}` }
                });
              } catch (logoutError) {
                // Ignore logout errors
              }
            }
          }
        }}
        confirmLoading={updatingCloudService}
        width={600}
      >
        <Form form={updateCloudForm} layout="vertical">
          <Form.Item
            label="Token Format Version"
            name="token_format_version"
            tooltip="Version of the token format to use"
          >
            <Select placeholder="Select version">
              <Select.Option value="v5">v5</Select.Option>
              <Select.Option value="v6">v6</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="Sandbox Mode"
            name="use_sandbox"
            tooltip="Enable or disable sandbox mode"
          >
            <Radio.Group>
              <Radio value="true">Enabled</Radio>
              <Radio value="false">Disabled</Radio>
            </Radio.Group>
          </Form.Item>
        </Form>
      </Modal>

      {/* Quick Guide Modal */}
      <Modal
        title="Mobile Test Pilot Quick Guide"
        open={quickGuideModalOpen}
        onCancel={() => setQuickGuideModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setQuickGuideModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={800}
        destroyOnClose
      >
        <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          <Typography.Title level={4}>Overview</Typography.Title>
          <Typography.Paragraph>
            Mobile Test Pilot (MTP) is a comprehensive test automation platform designed for FortiGate and FortiAuthenticator mobile applications.
            It provides a unified dashboard for managing virtual machines, physical devices, test files, and cloud services.
          </Typography.Paragraph>

          <Typography.Title level={4}>Main Components</Typography.Title>

          <Typography.Title level={5}>1. Virtual Machines (VMs)</Typography.Title>
          <ul>
            <li><strong>Management:</strong> Add, edit, and monitor VMs for testing</li>
            <li><strong>Platforms:</strong> Supports FortiGate and FortiAuthenticator VMs</li>
            <li><strong>Actions:</strong> Start tests, SSH access, web access</li>
            <li><strong>Monitoring:</strong> Real-time resource usage and test status</li>
          </ul>

          <Typography.Title level={5}>2. Cloud Services</Typography.Title>
          <ul>
            <li><strong>Integration:</strong> Connect to cloud-based test environments</li>
            <li><strong>Configuration:</strong> Manage cloud service connection details</li>
            <li><strong>Testing:</strong> Run tests directly on cloud services</li>
          </ul>

          <Typography.Title level={5}>3. Physical Devices</Typography.Title>
          <ul>
            <li><strong>Device Management:</strong> Register and manage iOS/Android devices</li>
            <li><strong>Streaming:</strong> Live video streaming of device screens</li>
            <li><strong>Control:</strong> Remote control devices for manual testing</li>
            <li><strong>Automation:</strong> Execute automated tests on physical devices</li>
          </ul>

          <Typography.Title level={5}>4. Test Files</Typography.Title>
          <ul>
            <li><strong>File Management:</strong> Upload and organize APK/IPA files</li>
            <li><strong>Metadata:</strong> Track file versions, platforms, and test scopes</li>
            <li><strong>Distribution:</strong> Distribute files to test environments</li>
          </ul>

          <Typography.Title level={4}>Key Features</Typography.Title>

          <Typography.Title level={5}>AI-Powered Analysis</Typography.Title>
          <ul>
            <li><strong>Log Analysis:</strong> Automatic analysis of test logs using Claude AI</li>
            <li><strong>Issue Detection:</strong> Smart identification of test failures and anomalies</li>
            <li><strong>Recommendations:</strong> Actionable insights for test improvement</li>
          </ul>

          <Typography.Title level={5}>Test Execution</Typography.Title>
          <ul>
            <li><strong>Docker Containers:</strong> Isolated test environments for consistent results</li>
            <li><strong>Template System:</strong> Predefined test configurations for quick execution</li>
            <li><strong>Parallel Testing:</strong> Run tests across multiple devices/environments simultaneously</li>
            <li><strong>Real-time Monitoring:</strong> Live test progress and resource utilization</li>
          </ul>

          <Typography.Title level={5}>FortiAuthenticator Specific</Typography.Title>
          <ul>
            <li><strong>API Testing:</strong> Built-in connectivity verification with FAC API</li>
            <li><strong>Token Management:</strong> Test FTK (hardware) and FTC (mobile) token assignments</li>
            <li><strong>User Provisioning:</strong> Automated creation and deletion of test users</li>
          </ul>

          <Typography.Title level={4}>Getting Started</Typography.Title>
          <ol>
            <li>Add a VM or Cloud Service using the "Add New" button</li>
            <li>Configure connection details (IP, credentials, API keys)</li>
            <li>Upload test files (APK/IPA) in the Files section</li>
            <li>Register physical devices in the Devices section</li>
            <li>Run tests using the "Start" button on any testbed</li>
            <li>Monitor results in real-time with live logs and metrics</li>
          </ol>

          <Typography.Title level={4}>Advanced Features</Typography.Title>
          <ul>
            <li><strong>SSH Console:</strong> Direct terminal access to VMs via WebSocket</li>
            <li><strong>Web Access:</strong> Built-in browser for GUI testing</li>
            <li><strong>Test Templates:</strong> Save and reuse test configurations</li>
            <li><strong>Reporting:</strong> Detailed test reports with screenshots and logs</li>
            <li><strong>Integration:</strong> Jenkins CI/CD pipeline support</li>
          </ul>
        </div>
      </Modal>

      {/* FAC Test Modal */}
      <Modal
        title={`Test FortiAuthenticator - ${selectedFacVm?.name || ''}`}
        open={facTestModalOpen}
        onCancel={() => setFacTestModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setFacTestModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={400}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Text>Perform tests to verify FortiAuthenticator functionality:</Typography.Text>

          {/* Display last FAC test timestamp if available */}
          {facTestResults.lastTestTimestamp && (
            <Alert
              type="info"
              message="Last Successful FAC Test"
              description={`Completed: ${new Date(facTestResults.lastTestTimestamp).toLocaleString()}`}
              showIcon
            />
          )}

          <Space>
            <Button
              type="primary"
              onClick={() => testFacConnectivity(selectedFacVm?.id)}
              loading={facTestResults.connectivity?.loading}
            >
              Test API Connection
            </Button>
            <Button
              type="default"
              onClick={() => testFacUserCreation(selectedFacVm?.id)}
              loading={facTestResults.userCreation?.loading}
            >
              Test Token Assignment
            </Button>
          </Space>

          {/* Display test results */}
          {facTestResults.connectivity && (
            <div style={{ marginTop: 16 }}>
              <Typography.Title level={5}>API Connection Test</Typography.Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                {facTestResults.connectivity.success ? (
                  <Tag color="success">Success</Tag>
                ) : (
                  <Tag color="error">Failed</Tag>
                )}
                <Typography.Text>{facTestResults.connectivity.message}</Typography.Text>
                {facTestResults.connectivity.timestamp && (
                  <Typography.Text type="secondary" style={{ fontSize: '0.9em' }}>
                    Last tested: {new Date(facTestResults.connectivity.timestamp).toLocaleString()}
                  </Typography.Text>
                )}
              </Space>
            </div>
          )}

          {facTestResults.userCreation && (
            <div style={{ marginTop: 16 }}>
              <Typography.Title level={5}>Token Assignment Test</Typography.Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                {facTestResults.userCreation.success ? (
                  <Tag color="success">Success</Tag>
                ) : (
                  <Tag color="error">Failed</Tag>
                )}
                <Typography.Text>FTK: {facTestResults.userCreation.ftkMessage}</Typography.Text>
                <Typography.Text>FTC: {facTestResults.userCreation.ftcMessage}</Typography.Text>
                {facTestResults.userCreation.timestamp && (
                  <Typography.Text type="secondary" style={{ fontSize: '0.9em' }}>
                    Last tested: {new Date(facTestResults.userCreation.timestamp).toLocaleString()}
                  </Typography.Text>
                )}
              </Space>
            </div>
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default VMs;
