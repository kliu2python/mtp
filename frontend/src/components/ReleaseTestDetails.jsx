import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Descriptions, Form, Input, Modal, Row, Select, Space, Table, Tag, message, Divider, Popover, Spin } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const ReleaseTestDetails = () => {
  const { platform, version } = useParams();
  const navigate = useNavigate();
  const [tests, setTests] = useState([]);
  const [parentTests, setParentTests] = useState([]); // Parent tests only
  const [subTasks, setSubTasks] = useState([]); // Sub-tasks only
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // create, edit, or view
  const [editingTest, setEditingTest] = useState(null);
  const [viewingTest, setViewingTest] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [jenkinsModalOpen, setJenkinsModalOpen] = useState(false);
  const [jenkinsLoading, setJenkinsLoading] = useState(false);
  const [jenkinsForm] = Form.useForm();
  const [pipelineMode, setPipelineMode] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState(['android', 'ios']);
  // Version selection state
  const [selectedAndroidVersions, setSelectedAndroidVersions] = useState(['android_15']);
  const [selectedIosVersions, setSelectedIosVersions] = useState(['ios_16']);

  // Android versions: android_15, android_14, android_13, android_12, android_11, android_10
  const androidVersions = [
    { label: 'Android 15', value: 'android_15' },
    { label: 'Android 14', value: 'android_14' },
    { label: 'Android 13', value: 'android_13' },
    { label: 'Android 12', value: 'android_12' },
    { label: 'Android 11', value: 'android_11' },
    { label: 'Android 10', value: 'android_10' },
  ];

  // iOS versions: ios_26, ios_18, ios_17, ios_16, ios_15
  const iosVersions = [
    { label: 'iOS 26', value: 'ios_26' },
    { label: 'iOS 18', value: 'ios_18' },
    { label: 'iOS 17', value: 'ios_17' },
    { label: 'iOS 16', value: 'ios_16' },
    { label: 'iOS 15', value: 'ios_15' },
  ];

  const handleAndroidVersionChange = (values) => {
    if (values.includes('select_all')) {
      setSelectedAndroidVersions(androidVersions.map(v => v.value));
    } else if (values.includes('')) {
      setSelectedAndroidVersions([]);
    } else {
      setSelectedAndroidVersions(values);
    }
  };

  const handleIosVersionChange = (values) => {
    if (values.includes('select_all')) {
      setSelectedIosVersions(iosVersions.map(v => v.value));
    } else if (values.includes('')) {
      setSelectedIosVersions([]);
    } else {
      setSelectedIosVersions(values);
    }
  };

  // Admin state
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [adminToken, setAdminToken] = useState(null);

  // Check admin login status on mount
  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      setIsAdminLoggedIn(true);
      setAdminToken(token);
    }
  }, []);

  // Get project from URL query params
  const urlParams = new URLSearchParams(window.location.search);
  const projectParam = urlParams.get('project');

  // Project mapping for display
  const projectMap = {
    'ftm': 'FTM',
    'fortiexplorer': 'FortiExplorer GO',
    'fortiedr': 'FortiEDR Mobile'
  };

  useEffect(() => {
    if (platform) {
      fetchTestsByPlatformAndVersion();
    }
  }, [platform, version]);

  const fetchTestsByPlatformAndVersion = async () => {
    try {
      setLoading(true);
      // Fetch tests filtered by platform and optionally by version
      const params = { platform: platform };
      if (version) {
        params.version = version;
      }

      // Also filter by project if it's in the URL query params
      const urlParams = new URLSearchParams(window.location.search);
      const projectParam = urlParams.get('project');
      if (projectParam) {
        params.project = projectParam;
      }

      const response = await axios.get(`${API_URL}/api/release-tests`, {
        params: params
      });

      // Separate parent tests and sub-tasks
      const allTests = response.data || [];
      const parents = [];
      const subtasks = [];

      allTests.forEach(test => {
        const isSubtask = test.test_metadata?.is_subtask ||
                          test.platform?.includes('_fac_token') ||
                          test.platform?.includes('_fgt_token') ||
                          test.platform?.includes('_ftc_token_on_fac') ||
                          test.platform?.includes('_ftc_token_on_fgt');

        if (isSubtask) {
          subtasks.push(test);
        } else {
          parents.push(test);
        }
      });

      setTests(allTests);
      setParentTests(parents);
      setSubTasks(subtasks);
      setLoading(false);
    } catch (error) {
      console.log('=== DEBUG: Error fetching release tests ===', error);
      // Only show error message if it's not a 404 (empty results)
      if (error.response?.status !== 404) {
        message.error('Failed to fetch release tests');
      }
      setLoading(false);
    }
  };

  // Polling for auto-refresh - every 5 minutes
  const startPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }
    pollTimerRef.current = setInterval(() => {
      if (autoRefresh) {
        pollStatusUpdates();
      }
    }, 300000); // 5 minutes (300000ms)
  };

  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const refreshTests = async () => {
    try {
      setLoading(true);
      await fetchTestsByPlatformAndVersion();
      // Also refresh subtask status if there's a build number
      if (tests.length > 0) {
        await axios.get(`${API_URL}/api/release-tests/refresh-subtasks/${tests[0]?.build_number}`);
      }
      message.success('Release tests refreshed');
    } catch (error) {
      message.error('Failed to refresh release tests');
    } finally {
      setLoading(false);
    }
  };


  // Get OS version from platform string - just the number
  const getOsVersion = (platformStr) => {
    if (!platformStr) return '';
    const platformLower = platformStr.toLowerCase();
    if (platformLower.includes('android')) {
      const match = platformStr.match(/android_(\d+)/i);
      return match ? match[1] : platformStr;
    }
    if (platformLower.includes('ios')) {
      const match = platformStr.match(/ios_(\d+)/i);
      return match ? match[1] : platformStr;
    }
    return platformStr.replace(/[^0-9]/g, '');
  };

  const handleStartJenkinsTest = () => {
    jenkinsForm.resetFields();
    setPipelineMode(false); // Default to single platform mode
    setJenkinsModalOpen(true);
  };

  const handleJenkinsSubmit = async () => {
    try {
      const values = await jenkinsForm.validateFields();
      const { build_number, dns } = values;

      setJenkinsLoading(true);

      // Trigger Jenkins jobs via backend API with version support
      // Only trigger the platform matching the current page
      await axios.post(
        `${API_URL}/api/release-tests/trigger-versioned`,
        {},
        {
          params: {
            build_number: build_number,
            dns: dns || undefined,
            android_versions: selectedAndroidVersions.join(','),
            ios_versions: selectedIosVersions.join(','),
            version: version,
            project: projectParam,
            platform_filter: platform // Pass current platform to filter
          }
        }
      );
      message.success('Jenkins tests triggered! Test records created. Status will update automatically...');

      setJenkinsModalOpen(false);
      jenkinsForm.resetFields();
      // Refresh to show newly created test records (they will be in 'pending' status)
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      console.error('Error triggering Jenkins test:', error);
      message.error('Failed to trigger Jenkins test');
    } finally {
      setJenkinsLoading(false);
    }
  };

  const handleCreateTest = () => {
    form.resetFields();
    form.setFieldsValue({
      platform: platform,
      version: version,
      project: projectParam || 'ftm'
    });
    setModalMode('create');
    setEditingTest(null);
    setModalOpen(true);
  };

  const handleEditTest = async (test) => {
    console.log('=== DEBUG: handleEditTest called with test ===', test);

    try {
      // Make sure test cases are available
      console.log('Checking test cases availability in edit mode...');
      console.log('Direct test_cases:', test.test_cases);
      console.log('Metadata test_cases:', test.metadata?.test_cases);

      // Always try to fetch test cases from the backend to ensure we have the latest data
      console.log('Fetching test cases from API to ensure latest data in edit mode...');
      try {
        const response = await axios.get(`${API_URL}/api/release-tests/${test.id}/test-cases`);
        console.log('API response for test cases in edit mode:', response.data);
        test.test_cases = response.data.test_cases || [];
        console.log('Updated test cases from API in edit mode:', test.test_cases);
      } catch (error) {
        console.log('Failed to fetch test cases from API in edit mode, checking existing data...', error);
        // If we can't fetch test cases, check existing data
        if (!test.test_cases || test.test_cases.length === 0) {
          console.log('No direct test cases found in edit mode, checking metadata...');
          // If test cases aren't directly on the test object, check metadata
          if (test.metadata && test.metadata.test_cases) {
            console.log('Found test cases in metadata in edit mode, using them');
            test.test_cases = test.metadata.test_cases;
          } else {
            // If we can't fetch test cases, ensure we have an empty array
            test.test_cases = [];
          }
        } else {
          console.log('Test cases already available directly on test object in edit mode');
        }
      }

      console.log('Final test_cases for edit display:', test.test_cases);
      console.log('Test cases count in edit mode:', test.test_cases.length);

      form.setFieldsValue({
        build_number: test.build_number,
        platform: test.platform,
        version: test.version,
        project: test.project || 'ftm',
        test_suite: test.test_suite,
        test_type: test.test_type,
        status: test.status,
        started_at: test.started_at ? new Date(test.started_at) : null,
        completed_at: test.completed_at ? new Date(test.completed_at) : null,
        duration: test.duration,
        passed_count: test.passed_count,
        failed_count: test.failed_count,
        skipped_count: test.skipped_count,
        jenkins_job_name: test.jenkins_job_name,
        jenkins_build_number: test.jenkins_build_number,
        jenkins_build_url: test.jenkins_build_url,
        apk_file_id: test.apk_file_id
      });
      setModalMode('edit');
      setEditingTest(test);
      setModalOpen(true);
    } catch (error) {
      console.log('Error in handleEditTest:', error);
      message.error('Failed to prepare test for editing');
      // Still allow editing even if we can't fetch additional data
      // Make sure test cases are available
      if (!test.test_cases) {
        if (test.metadata && test.metadata.test_cases) {
          test.test_cases = test.metadata.test_cases;
        } else {
          test.test_cases = [];
        }
      }

      form.setFieldsValue({
        build_number: test.build_number,
        platform: test.platform,
        version: test.version,
        project: test.project || 'ftm',
        test_suite: test.test_suite,
        test_type: test.test_type,
        status: test.status,
        started_at: test.started_at ? new Date(test.started_at) : null,
        completed_at: test.completed_at ? new Date(test.completed_at) : null,
        duration: test.duration,
        passed_count: test.passed_count,
        failed_count: test.failed_count,
        skipped_count: test.skipped_count,
        jenkins_job_name: test.jenkins_job_name,
        jenkins_build_number: test.jenkins_build_number,
        jenkins_build_url: test.jenkins_build_url,
        apk_file_id: test.apk_file_id
      });
      setModalMode('edit');
      setEditingTest(test);
      setModalOpen(true);
    }
  };

  const handleViewTest = async (test) => {
    console.log('=== DEBUG: handleViewTest called with test ===', test);

    try {
      // Make sure test cases are available
      console.log('Checking test cases availability...');
      console.log('Direct test_cases:', test.test_cases);
      console.log('Metadata test_cases:', test.metadata?.test_cases);

      // Always try to fetch test cases from the backend to ensure we have the latest data
      console.log('Fetching test cases from API to ensure latest data...');
      try {
        const response = await axios.get(`${API_URL}/api/release-tests/${test.id}/test-cases`);
        console.log('API response for test cases:', response.data);
        test.test_cases = response.data.test_cases || [];
        console.log('Updated test cases from API:', test.test_cases);
      } catch (error) {
        console.log('Failed to fetch test cases from API, checking existing data...', error);
        // If we can't fetch test cases, check existing data
        if (!test.test_cases || test.test_cases.length === 0) {
          console.log('No direct test cases found, checking metadata...');
          // If test cases aren't directly on the test object, check metadata
          if (test.metadata && test.metadata.test_cases) {
            console.log('Found test cases in metadata, using them');
            test.test_cases = test.metadata.test_cases;
          } else {
            // If we can't fetch test cases, ensure we have an empty array
            test.test_cases = [];
          }
        } else {
          console.log('Test cases already available directly on test object');
        }
      }

      console.log('Final test_cases for display:', test.test_cases);
      console.log('Test cases count:', test.test_cases.length);

      // Fetch Mantis issues if they exist
      if (test.metadata && test.metadata.mantis_issues && test.metadata.mantis_issues.length > 0) {
        try {
          const response = await axios.get(`${API_URL}/api/release-tests/${test.id}/mantis-issues`);
          test.mantis_issues = response.data.mantis_issues;
        } catch (error) {
          console.log('Failed to fetch Mantis issues:', error);
        }
      }

      form.setFieldsValue({
        build_number: test.build_number,
        platform: test.platform,
        version: test.version,
        project: test.project || 'ftm',
        test_suite: test.test_suite,
        test_type: test.test_type,
        status: test.status,
        started_at: test.started_at ? new Date(test.started_at) : null,
        completed_at: test.completed_at ? new Date(test.completed_at) : null,
        duration: test.duration,
        passed_count: test.passed_count,
        failed_count: test.failed_count,
        skipped_count: test.skipped_count,
        jenkins_job_name: test.jenkins_job_name,
        jenkins_build_number: test.jenkins_build_number,
        jenkins_build_url: test.jenkins_build_url,
        apk_file_id: test.apk_file_id
      });
      setModalMode('view');
      setViewingTest(test);
      setModalOpen(true);
    } catch (error) {
      console.log('Error in handleViewTest:', error);
      message.error('Failed to fetch additional data');
      // Still show the test even if additional data failed to load
      // Make sure test cases are available
      if (!test.test_cases) {
        if (test.metadata && test.metadata.test_cases) {
          test.test_cases = test.metadata.test_cases;
        } else {
          test.test_cases = [];
        }
      }

      form.setFieldsValue({
        build_number: test.build_number,
        platform: test.platform,
        version: test.version,
        project: test.project || 'ftm',
        test_suite: test.test_suite,
        test_type: test.test_type,
        status: test.status,
        started_at: test.started_at ? new Date(test.started_at) : null,
        completed_at: test.completed_at ? new Date(test.completed_at) : null,
        duration: test.duration,
        passed_count: test.passed_count,
        failed_count: test.failed_count,
        skipped_count: test.skipped_count,
        jenkins_job_name: test.jenkins_job_name,
        jenkins_build_number: test.jenkins_build_number,
        jenkins_build_url: test.jenkins_build_url,
        apk_file_id: test.apk_file_id
      });
      setModalMode('view');
      setViewingTest(test);
      setModalOpen(true);
    }
  };

  const handleDeleteTest = async (testId) => {
    try {
      await axios.delete(`${API_URL}/api/release-tests/${testId}`);
      message.success('Release test deleted successfully');
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      message.error('Failed to delete release test');
    }
  };

  const handleSaveTest = async () => {
    try {
      const values = await form.validateFields();

      // Process date fields
      if (values.started_at) {
        values.started_at = values.started_at.toISOString();
      }
      if (values.completed_at) {
        values.completed_at = values.completed_at.toISOString();
      }

      setSaving(true);

      if (modalMode === 'edit' && editingTest) {
        await axios.put(`${API_URL}/api/release-tests/${editingTest.id}`, values);
        message.success('Release test updated successfully');
      } else {
        // For create mode, ensure platform and version are set
        values.platform = values.platform || platform;
        values.version = values.version || version;

        // Handle multiple copies creation
        const copyCount = values.copy_count || 1;
        // Remove copy_count from values as it's not needed by the backend
        const { copy_count, ...apiValues } = values;
        let successCount = 0;

        for (let i = 0; i < copyCount; i++) {
          try {
            await axios.post(`${API_URL}/api/release-tests`, apiValues);
            successCount++;
          } catch (error) {
            console.error(`Failed to create copy ${i + 1}:`, error);
            if (copyCount === 1) {
              throw error; // Re-throw for single copy to show error message
            }
          }
        }

        if (successCount > 0) {
          if (successCount === copyCount) {
            message.success(`Successfully created ${successCount} release test(s)`);
          } else {
            message.warning(`Created ${successCount} of ${copyCount} release tests. Some failed.`);
          }
        } else {
          throw new Error('Failed to create any release tests');
        }
      }

      setModalOpen(false);
      form.resetFields();
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      message.error('Failed to save release test');
    } finally {
      setSaving(false);
    }
  };

  const handlePopulateFromAllure = async () => {
    try {
      const values = await form.validateFields();

      // Need to have a test ID to populate from Allure
      if (modalMode !== 'edit' || !editingTest) {
        message.error('Please save the test first before populating from Allure');
        return;
      }

      // Need to have a Jenkins build URL
      const jenkinsUrl = values.jenkins_build_url;
      if (!jenkinsUrl) {
        message.error('Please enter a Jenkins build URL first');
        return;
      }

      // Construct Allure URL (assuming it's the same base URL + /allure)
      const allureUrl = jenkinsUrl.endsWith('/') ? `${jenkinsUrl}allure` : `${jenkinsUrl}/allure`;

      setSaving(true);

      // Call the backend API to populate from Allure
      await axios.post(`${API_URL}/api/release-tests/populate-from-allure`, null, {
        params: {
          test_id: editingTest.id,
          allure_url: allureUrl
        }
      });

      message.success('Release test populated from Allure report successfully');
      setModalOpen(false);
      form.resetFields();
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      message.error('Failed to populate release test from Allure report');
    } finally {
      setSaving(false);
    }
  };

  const handlePopulateFromZip = async () => {
    // Create a hidden file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.zip';
    fileInput.style.display = 'none';

    fileInput.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) {
        return;
      }

      // Validate file type
      if (!file.name.endsWith('.zip')) {
        message.error('Please select a ZIP file');
        return;
      }

      setSaving(true);

      try {
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('file', file);

        // Call the backend API to upload and populate from ZIP
        await axios.post(`${API_URL}/api/release-tests/${editingTest.id}/upload-zip`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        message.success('Release test populated from ZIP file successfully');
        setModalOpen(false);
        form.resetFields();
        fetchTestsByPlatformAndVersion();
      } catch (error) {
        message.error('Failed to populate release test from ZIP file');
      } finally {
        setSaving(false);
      }
    };

    // Trigger file selection
    document.body.appendChild(fileInput);
    fileInput.click();
    document.body.removeChild(fileInput);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return 'green';
      case 'failed': return 'red';
      case 'running': return 'blue';
      case 'pending': return 'orange';
      default: return 'default';
    }
  };

  const columns = [
    {
      title: 'Build Number',
      dataIndex: 'build_number',
      key: 'build_number',
      sorter: (a, b) => a.build_number.localeCompare(b.build_number),
    },
    {
      title: 'OS Version',
      key: 'os_version',
      render: (_, record) => {
        const osVer = getOsVersion(record.platform);
        return <Tag>{osVer}</Tag>;
      },
      sorter: (a, b) => getOsVersion(a.platform).localeCompare(getOsVersion(b.platform)),
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform, record) => {
        // Check if this is a sub-task
        const isSubtask = record.test_metadata?.is_subtask || record.platform?.includes('_fac_token') ||
                          record.platform?.includes('_fgt_token') ||
                          record.platform?.includes('_ftc_token_on_fac') ||
                          record.platform?.includes('_ftc_token_on_fgt');

        let displayName = platform ? platform.toString().toUpperCase() : 'UNKNOWN';
        let color = 'default';

        if (isSubtask) {
          // Display sub-task name
          const taskName = record.test_metadata?.task_name || record.test_metadata?.task_display || '';
          const taskDisplay = record.test_metadata?.task_display || taskName;
          displayName = taskDisplay;
          color = 'purple';
        } else {
          // Map platform to display name for parent tasks
          const platformDisplay = {
            'android_15': 'Android 15',
            'android_14': 'Android 14',
            'android_13': 'Android 13',
            'android_12': 'Android 12',
            'android_11': 'Android 11',
            'android_10': 'Android 10',
            'ios_26': 'iOS 26',
            'ios_18': 'iOS 18',
            'ios_17': 'iOS 17',
            'ios_16': 'iOS 16',
            'ios_15': 'iOS 15',
            'android': 'Android',
            'ios': 'iOS'
          };
          displayName = platformDisplay[platform] || (platform ? platform.toString().toUpperCase() : 'UNKNOWN');
          color = platform?.includes('android') ? 'green' : platform?.includes('ios') ? 'blue' : 'default';
        }

        return <Tag color={color}>{displayName}</Tag>;
      },
      filters: [
        { text: 'Android 15', value: 'android_15' },
        { text: 'Android 14', value: 'android_14' },
        { text: 'Android 13', value: 'android_13' },
        { text: 'Android 12', value: 'android_12' },
        { text: 'Android 11', value: 'android_11' },
        { text: 'Android 10', value: 'android_10' },
        { text: 'iOS 26', value: 'ios_26' },
        { text: 'iOS 18', value: 'ios_18' },
        { text: 'iOS 17', value: 'ios_17' },
        { text: 'iOS 16', value: 'ios_16' },
        { text: 'iOS 15', value: 'ios_15' }
      ],
      onFilter: (value, record) => record.platform === value || record.platform?.startsWith(value),
    },
    {
      title: 'Test Suite',
      dataIndex: 'test_suite',
      key: 'test_suite',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{(status || 'PENDING')?.toString()?.toUpperCase()}</Tag>,
      filters: [
        { text: 'Pending', value: 'pending' },
        { text: 'Running', value: 'running' },
        { text: 'Passed', value: 'passed' },
        { text: 'Failed', value: 'failed' },
        { text: 'Skipped', value: 'skipped' },
        { text: 'Error', value: 'error' }
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'Results',
      key: 'results',
      render: (_, record) => {
        // Debug: log the record to see its structure
        console.log('DEBUG Results column - record:', record);

        // Calculate counts based on actual test cases if available
        let passedCount = record.passed_count || 0;
        let failedCount = record.failed_count || 0;
        let skippedCount = record.skipped_count || 0;

        // If test cases are available, recalculate based on actual data
        if (record.test_cases && Array.isArray(record.test_cases)) {
          console.log('DEBUG: Found test_cases array with length:', record.test_cases.length);
          passedCount = record.test_cases.filter(tc => {
            const status = tc.status ? tc.status.toString().toUpperCase() : '';
            console.log('DEBUG: Test case status:', tc.status, '-> processed:', status);
            return status === 'PASSED';
          }).length;

          failedCount = record.test_cases.filter(tc => {
            const status = tc.status ? tc.status.toString().toUpperCase() : '';
            return status === 'FAILED' || status === 'BROKEN';
          }).length;

          skippedCount = record.test_cases.filter(tc => {
            const status = tc.status ? tc.status.toString().toUpperCase() : '';
            return status === 'SKIPPED';
          }).length;

          console.log('DEBUG: Calculated counts - Passed:', passedCount, 'Failed:', failedCount, 'Skipped:', skippedCount);
        } else {
          console.log('DEBUG: No test_cases array found, using original counts');
        }

        return (
          <Space size="small">
            <Tag color="green">{passedCount} Passed</Tag>
            <Tag color="red">{failedCount} Failed</Tag>
            <Tag color="orange">{skippedCount} Skipped</Tag>
          </Space>
        );
      },
    },
    {
      title: 'Component',
      key: 'component',
      render: (_, record) => {
        // Extract component info from the first test case if available
        if (record.test_cases && record.test_cases.length > 0) {
          const firstTestCase = record.test_cases[0];
          return firstTestCase.test_component || 'N/A';
        }
        return 'N/A';
      },
    },
    {
      title: 'Platform',
      key: 'test_platform',
      render: (_, record) => {
        // Extract platform info from the first test case if available
        if (record.test_cases && record.test_cases.length > 0) {
          const firstTestCase = record.test_cases[0];
          return firstTestCase.test_platform || 'N/A';
        }
        return 'N/A';
      },
    },
    {
      title: 'Device',
      key: 'device',
      render: (_, record) => {
        // Extract device info from the first test case if available
        if (record.test_cases && record.test_cases.length > 0) {
          const firstTestCase = record.test_cases[0];
          return firstTestCase.device_info || 'N/A';
        }
        return 'N/A';
      },
    },
    {
      title: 'Test Type',
      dataIndex: 'test_type',
      key: 'test_type',
      render: (testType) => {
        const testTypeMap = {
          'smoke': 'Smoke',
          'full': 'Full',
          'critical': 'Critical Path'
        };
        return testTypeMap[testType] || testType || 'N/A';
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewTest(record)}
          >
            View
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditTest(record)}
          >
            Edit
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteTest(record.id)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={`Release Tests${projectParam ? ` - ${projectMap[projectParam] || projectParam.toUpperCase()}` : ''}${platform ? ` - ${platform.toUpperCase()}` : ''}${version ? ` - Version ${version}` : ''}`}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={refreshTests}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStartJenkinsTest}
            >
              Start Release Test
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={handleCreateTest}
            >
              Upload Report
            </Button>
            <Button
              onClick={() => navigate('/release-tests')}
            >
              Back to Platforms
            </Button>
            {isAdminLoggedIn && (
              <Button
                icon={<SettingOutlined />}
                onClick={() => navigate('/admin')}
                style={{ borderColor: '#52c41a', color: '#52c41a' }}
              >
                Config Default Payload
              </Button>
            )}
          </Space>
        }
      >
        {/* Parent Tests Table */}
        <div style={{ marginBottom: 16 }}>
          <h3>Parent Tests</h3>
          <Table
            dataSource={parentTests}
            columns={columns}
            rowKey="id"
            loading={false}
            pagination={{ pageSize: 5 }}
            scroll={{ x: 'max-content' }}
            size="small"
          />
        </div>

        {/* Sub-Tasks Table */}
        <Divider />
        <div>
          <h3>Pipeline Sub-Tasks</h3>
          <Table
            dataSource={subTasks}
            columns={[
              {
                title: 'Task Name',
                key: 'task_name',
                render: (_, record) => {
                  const taskName = record.test_metadata?.task_name || '';
                  const taskDisplay = record.test_metadata?.task_display || taskName;
                  return <Tag color="purple">{taskDisplay || taskName}</Tag>;
                }
              },
              {
                title: 'OS Version',
                key: 'os_version',
                render: (_, record) => {
                  const osVer = getOsVersion(record.platform);
                  return <Tag>{osVer}</Tag>;
                }
              },
              {
                title: 'Status',
                key: 'status',
                render: (status) => {
                  const statusStr = status ? status.toString() : '';
                  const statusUpper = (statusStr || 'PENDING').toUpperCase();
                  let color = 'default';
                  let icon = null;

                  if (statusUpper === 'SUCCESS' || statusUpper === 'PASSED') {
                    color = 'green';
                    icon = <CheckCircleOutlined />;
                  } else if (statusUpper === 'FAILURE' || statusUpper === 'FAILED') {
                    color = 'red';
                    icon = <CloseCircleOutlined />;
                  } else if (statusUpper === 'RUNNING' || statusUpper === 'BUILDING') {
                    color = 'blue';
                    icon = <SyncOutlined spin />;
                  } else if (statusUpper === 'PENDING' || statusUpper === 'WAITING') {
                    color = 'orange';
                    icon = <ClockCircleOutlined />;
                  }

                  return (
                    <Tag color={color}>
                      {icon} {statusUpper}
                    </Tag>
                  );
                }
              },
              {
                title: 'Jenkins URL',
                key: 'jenkins_url',
                render: (_, record) => (
                  <a href={record.jenkins_build_url || '#'} target="_blank" rel="noopener noreferrer">
                    {record.jenkins_build_number ? `Build #${record.jenkins_build_number}` : 'Waiting...'}
                  </a>
                )
              },
              {
                title: 'Results',
                key: 'results',
                render: (_, record) => (
                  <Space size="small">
                    <Tag color="green">{record.passed_count || 0} Passed</Tag>
                    <Tag color="red">{record.failed_count || 0} Failed</Tag>
                    <Tag color="orange">{record.skipped_count || 0} Skipped</Tag>
                  </Space>
                )
              }
            ]}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ x: 'max-content' }}
            size="small"
          />
        </div>
      </Card>

      {/* Create/Edit/View Modal */}
      <Modal
        title={
          modalMode === 'edit' ? 'Edit Release Test' :
          modalMode === 'view' ? 'View Release Test' : 'Create Release Test'
        }
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        onOk={modalMode === 'view' ? null : handleSaveTest}
        okText={modalMode === 'view' ? 'Close' : 'Save'}
        confirmLoading={saving}
        width={800}
        footer={[
          ...(modalMode === 'view' ? [] : [
            <Button key="save" type="primary" loading={saving} onClick={handleSaveTest}>
              Save
            </Button>
          ]),
          ...(modalMode === 'edit' ? [
            <Button key="populate-allure" loading={saving} onClick={handlePopulateFromAllure}>
              Populate from Allure
            </Button>
          ] : []),
          ...(modalMode === 'edit' ? [
            <Button key="populate-zip" loading={saving} onClick={handlePopulateFromZip}>
              Populate from ZIP
            </Button>
          ] : []),
          <Button key="cancel" onClick={() => {
            setModalOpen(false);
            form.resetFields();
          }}>
            {modalMode === 'view' ? 'Close' : 'Cancel'}
          </Button>
        ]}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Build Number"
                name="build_number"
                rules={[{ required: true, message: 'Please enter build number' }]}
              >
                <Input placeholder="e.g., 1.2.3-rc1" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Platform"
                name="platform"
                rules={[{ required: true, message: 'Please select platform' }]}
              >
                <Select placeholder="Select platform" disabled={modalMode === 'view' || modalMode === 'create'}>
                  <Select.Option value="android">Android</Select.Option>
                  <Select.Option value="ios">iOS</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Version"
                name="version"
                rules={[{ required: true, message: 'Please enter version' }]}
              >
                <Input placeholder="e.g., 1.2.3" disabled={modalMode === 'view' || modalMode === 'create'} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Project"
                name="project"
                rules={[{ required: true, message: 'Please select project' }]}
              >
                <Select placeholder="Select project" disabled>
                  <Select.Option value="ftm">FTM</Select.Option>
                  <Select.Option value="fortiexplorer">FortiExplorer GO</Select.Option>
                  <Select.Option value="fortiedr">FortiEDR Mobile</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Test Suite"
                name="test_suite"
                rules={[{ required: true, message: 'Please enter test suite' }]}
              >
                <Select placeholder="Select test suite" disabled={modalMode === 'view'}>
                  <Select.Option value="functional">Functional</Select.Option>
                  <Select.Option value="integration">Integration</Select.Option>
                  <Select.Option value="regression">Regression</Select.Option>
                  <Select.Option value="acceptance">Acceptance</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Test Type"
                name="test_type"
                rules={[{ required: true, message: 'Please enter test type' }]}
              >
                <Select placeholder="Select test type" disabled={modalMode === 'view'}>
                  <Select.Option value="smoke">Smoke</Select.Option>
                  <Select.Option value="full">Full</Select.Option>
                  <Select.Option value="critical">Critical Path</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Status"
                name="status"
              >
                <Select placeholder="Select status" disabled={modalMode === 'view'}>
                  <Select.Option value="pending">Pending</Select.Option>
                  <Select.Option value="running">Running</Select.Option>
                  <Select.Option value="passed">Passed</Select.Option>
                  <Select.Option value="failed">Failed</Select.Option>
                  <Select.Option value="skipped">Skipped</Select.Option>
                  <Select.Option value="error">Error</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            {modalMode === 'create' && (
              <Col span={12}>
                <Form.Item
                  label="Number of Copies"
                  name="copy_count"
                  initialValue={1}
                >
                  <Select>
                    <Select.Option value={1}>1</Select.Option>
                    <Select.Option value={2}>2</Select.Option>
                    <Select.Option value={3}>3</Select.Option>
                    <Select.Option value={4}>4</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            )}
          </Row>
          {(modalMode === 'view' || modalMode === 'edit') && (
            <>
              {(() => {
                const currentTest = modalMode === 'view' ? viewingTest : editingTest;

                if (currentTest?.test_cases && currentTest.test_cases.length > 0) {
                  return (
                    <div style={{ marginTop: 20 }}>
                      <h3>Test Cases</h3>
                      <Table
                        dataSource={currentTest.test_cases.map((tc, index) => ({ ...tc, key: index }))}
                        columns={[
                          {
                            title: 'Name',
                            dataIndex: 'name',
                            key: 'name',
                            render: (_, record) => {
                              console.log('Rendering test case record:', record);
                              // Handle different data formats
                              // For Allure CSV format with test_method
                              if (record.test_method && record.name) {
                                return `${record.name} [${record.test_method}]`;
                              }
                              // For Allure CSV format with full name in 'Name' column
                              else if (record.name && !record.classname) {
                                return record.name;
                              }
                              // For traditional format with classname
                              else if (record.classname) {
                                return `${record.classname}.${record.name}`;
                              }
                              // Fallback
                              return record.name || 'Unknown Test';
                            }
                          },
                          {
                            title: 'Status',
                            dataIndex: 'status',
                            key: 'status',
                            render: (status) => {
                              let color = 'default';
                              const upperStatus = typeof status === 'string' ? status.toUpperCase() : status || 'UNKNOWN';
                              if (upperStatus === 'PASSED') color = 'green';
                              if (upperStatus === 'FAILED') color = 'red';
                              if (upperStatus === 'SKIPPED') color = 'orange';
                              if (upperStatus === 'BROKEN') color = 'volcano';
                              return <Tag color={color}>{upperStatus}</Tag>;
                            }
                          },
                          {
                            title: 'Duration',
                            dataIndex: 'duration_ms',
                            key: 'duration_ms',
                            render: (_, record) => {
                              // Handle both duration_ms (CSV) and time (XML) formats
                              if (record.duration_ms) {
                                return `${record.duration_ms} ms`;
                              } else if (record.time) {
                                return `${record.time} s`;
                              }
                              return 'N/A';
                            }
                          }
                        ]}
                        pagination={{ pageSize: 4 }}
                        size="small"
                      />
                    </div>
                  );
                }
                return null;
              })()}

              {modalMode === 'view' && viewingTest?.mantis_issues && viewingTest.mantis_issues.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <h3>Mantis Issues</h3>
                  <Table
                    dataSource={viewingTest.mantis_issues.map((issue, index) => ({ ...issue, key: index }))}
                    columns={[
                      {
                        title: 'ID',
                        dataIndex: 'issue_id',
                        key: 'issue_id',
                        render: (text, record) => (
                          <a href={record.url} target="_blank" rel="noopener noreferrer">
                            {text}
                          </a>
                        ),
                      },
                      {
                        title: 'Summary',
                        dataIndex: 'summary',
                        key: 'summary',
                      },
                      {
                        title: 'Status',
                        dataIndex: 'status',
                        key: 'status',
                        render: (status) => {
                          let color = 'default';
                          if (status === 'resolved') color = 'green';
                          if (status === 'feedback') color = 'orange';
                          if (status === 'assigned') color = 'blue';
                          return <Tag color={color}>{status}</Tag>;
                        }
                      },
                      {
                        title: 'Priority',
                        dataIndex: 'priority',
                        key: 'priority',
                      },
                      {
                        title: 'Severity',
                        dataIndex: 'severity',
                        key: 'severity',
                      }
                    ]}
                    pagination={{ pageSize: 5 }}
                    size="small"
                  />
                </div>
              )}
            </>
          )}
        </Form>
      </Modal>

      {/* Start Release Test Modal */}
      <Modal
        title={`Start Release Test - ${platform ? platform.toUpperCase() : ''}${version ? ` ${version}` : ''}`}
        open={jenkinsModalOpen}
        onCancel={() => {
          setJenkinsModalOpen(false);
          jenkinsForm.resetFields();
        }}
        onOk={handleJenkinsSubmit}
        okText="Start"
        confirmLoading={jenkinsLoading}
        width={700}
      >
        <Form form={jenkinsForm} layout="vertical">
          <Form.Item
            label="Build Number"
            name="build_number"
            rules={[{ required: true, message: 'Please enter build number' }]}
          >
            <Input placeholder="e.g., 0022, 0023" />
          </Form.Item>
          <Form.Item
            label="DNS (optional)"
            name="dns"
            rules={[
              {
                pattern: /^(null|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$/,
                message: 'Enter "null" or a valid IP address (e.g., 10.160.41.22)'
              }
            ]}
          >
            <Input placeholder="e.g., null or 10.160.41.22" />
          </Form.Item>
          {/* Only show Android versions if platform is android or no platform filter */}
          {(platform === 'android' || !platform || platform.startsWith('android')) && (
            <Form.Item
              label="Android Versions"
              name="android_versions"
              initialValue={['android_15']}
            >
              <Select
                mode="multiple"
                options={androidVersions}
                onChange={handleAndroidVersionChange}
              />
            </Form.Item>
          )}
          {/* Only show iOS versions if platform is ios or no platform filter */}
          {(platform === 'ios' || !platform || platform.startsWith('ios')) && (
            <Form.Item
              label="iOS Versions"
              name="ios_versions"
              initialValue={['ios_16']}
            >
              <Select
                mode="multiple"
                options={iosVersions}
                onChange={handleIosVersionChange}
              />
            </Form.Item>
          )}
          <Form.Item>
            <p style={{ fontSize: 12, color: '#666' }}>
              Will trigger Jenkins jobs for selected versions and fetch Allure reports automatically.
            </p>
            <p style={{ fontSize: 12, color: '#666' }}>
              {platform === 'android' || platform?.startsWith('android') ? (
                <>Android: {selectedAndroidVersions.join(', ') || 'None'}</>
              ) : platform === 'ios' || platform?.startsWith('ios') ? (
                <>iOS: {selectedIosVersions.join(', ') || 'None'}</>
              ) : (
                <>
                  Android: {selectedAndroidVersions.join(', ') || 'None'}
                  <br />
                  iOS: {selectedIosVersions.join(', ') || 'None'}
                </>
              )}
            </p>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReleaseTestDetails;