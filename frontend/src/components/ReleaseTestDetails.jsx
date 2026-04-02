import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Descriptions, Form, Input, Modal, Row, Select, Space, Table, Tag, message, Divider, Popover, Spin, Drawer } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import {
  DeleteOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  FileTextOutlined
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
  const [form] = Form.useForm();
  const [jenkinsModalOpen, setJenkinsModalOpen] = useState(false);
  const [jenkinsLoading, setJenkinsLoading] = useState(false);
  const [jenkinsForm] = Form.useForm();
  const [pipelineMode, setPipelineMode] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState(['android', 'ios']);
  // Version selection state
  const [selectedAndroidVersions, setSelectedAndroidVersions] = useState(['android_15']);
  const [selectedIosVersions, setSelectedIosVersions] = useState(['ios_16']);
  const [jenkinsSettings, setJenkinsSettings] = useState(null);
  const [testCasesDrawer, setTestCasesDrawer] = useState({ visible: false, testCases: [], currentTest: null });

  // Fetch Jenkins settings
  const fetchJenkinsSettings = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/settings`);
      setJenkinsSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch Jenkins settings:', error);
    }
  };

  // Get Jenkins job URL for a test record
  const getJenkinsJobUrl = (record) => {
    if (!jenkinsSettings) return null;

    const baseUrl = jenkinsSettings.jenkins_url?.replace(/\/$/, '') || '';
    const platform = record.platform || '';

    // Determine platform type (android or ios)
    const platformType = platform.toLowerCase().startsWith('ios') ? 'ios' : 'android';

    // Build the job URL based on the pattern:
    // http://jenkins_url/job/mobile_test/job/FortiToken_Mobile/job/[platform]/job/[version]/job/[version]_auto_fac_token/
    return `${baseUrl}/job/mobile_test/job/FortiToken_Mobile/job/${platformType}/job/${platform}/job/${platform}_auto_fac_token/`;
  };

  // Refresh Jenkins job status for a test record
  const handleRefreshJobStatus = async (record) => {
    try {
      const jobUrl = getJenkinsJobUrl(record);
      if (!jobUrl) {
        message.error('Jenkins settings not available');
        return;
      }

      // Get the started_at time from the test record
      const startTime = record.started_at || record.created_at;
      const timestamp = startTime ? new Date(startTime).toISOString() : new Date().toISOString();

      // Call the API to update job status
      await axios.post(
        `${API_URL}/api/jenkins/job-status/update`,
        {},
        {
          params: {
            job_url: jobUrl,
            timestamp: timestamp,
            job_name: record.platform || 'unknown'
          }
        }
      );

      message.success(`Job status refreshed for ${record.platform}`);

      // Refresh the test list
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      console.error('Error refreshing job status:', error);
      message.error('Failed to refresh job status: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Refresh all Jenkins job statuses
  const handleRefreshAllJobStatuses = async () => {
    try {
      const startTime = new Date().toISOString();

      // Update all test records
      const promises = tests.map(async (test) => {
        const jobUrl = getJenkinsJobUrl(test);
        if (!jobUrl) return;

        const timestamp = test.started_at || test.created_at || startTime;

        try {
          await axios.post(
            `${API_URL}/api/jenkins/job-status/update`,
            {},
            {
              params: {
                job_url: jobUrl,
                timestamp: timestamp,
                job_name: test.platform || 'unknown'
              }
            }
          );
        } catch (error) {
          console.error('Error refreshing job status for', test.platform, error);
        }
      });

      await Promise.all(promises);

      message.success('All job statuses refreshed');
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      console.error('Error refreshing all job statuses:', error);
      message.error('Failed to refresh all job statuses');
    }
  };

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
    // Fetch Jenkins settings on mount
    fetchJenkinsSettings();
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
      // Fetch tests filtered by version and project (no platform filter to get all platforms)
      const params = {};
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
      // We want to display subtasks (8 records), not parent tests (2 pipeline records)
      const allTests = response.data || [];
      const parents = [];
      const subtasks = [];

      allTests.forEach(test => {
        const isSubtask = test.metadata?.is_subtask ||
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
      // Display subtasks if available, otherwise display parent tests (for manual uploads)
      setParentTests(subtasks.length > 0 ? subtasks : parents);
      setSubTasks(subtasks);
      setLoading(false);

      // Auto-refresh Allure data for completed builds
      // Check if any test needs Allure data (has Jenkins build URL but no test counts)
      if (allTests.length > 0 && allTests[0]?.build_number) {
        const needsAllure = allTests.some(test =>
          test.jenkins_build_url &&
          ((!test.passed_count && test.passed_count !== 0) ||
           (!test.failed_count && test.failed_count !== 0) ||
           (!test.skipped_count && test.skipped_count !== 0))
        );

        if (needsAllure) {
          const buildNumber = allTests[0]?.build_number;
          console.log('Auto-triggering Allure refresh for build:', buildNumber, 'tests:', allTests.map(t => ({
            platform: t.platform,
            jenkins_build_url: t.jenkins_build_url,
            passed_count: t.passed_count,
            failed_count: t.failed_count,
            skipped_count: t.skipped_count
          })));

          // Trigger Allure refresh
          axios.get(`${API_URL}/api/release-tests/refresh-allure/${buildNumber}`)
            .then((response) => {
              console.log('Allure refresh result:', response.data);
              const count = response.data?.count || 0;
              if (count > 0) {
                // Data updated, reload the page to show new data
                console.log('Allure data updated, reloading page...');
                setTimeout(() => {
                  window.location.reload();
                }, 1000);
              } else {
                console.log('No Allure data available yet, will retry...');
                // No data yet, retry after 2 seconds
                setTimeout(() => {
                  window.location.reload();
                }, 2000);
              }
            })
            .catch(err => {
              console.log('Failed to refresh Allure data:', err);
              // Even on error, reload to show latest state
              setTimeout(() => {
                window.location.reload();
              }, 2000);
            });
        }
      }
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

  // Combined refresh all function - refresh subtasks, allure, and job statuses
  const handleRefreshAll = async () => {
    try {
      setLoading(true);
      if (tests.length > 0) {
        const buildNumber = tests[0]?.build_number;
        console.log('Refreshing all data for build:', buildNumber);

        // Refresh subtask status from Jenkins
        await axios.get(`${API_URL}/api/release-tests/refresh-subtasks/${buildNumber}`);

        // Refresh Allure data for completed builds
        const allureResponse = await axios.get(`${API_URL}/api/release-tests/refresh-allure/${buildNumber}`);
        console.log('Allure refresh result:', allureResponse.data);

        // Refresh all Jenkins job statuses
        await handleRefreshAllJobStatuses();

        // Re-fetch to show updated status
        await fetchTestsByPlatformAndVersion();

        message.success(`All data refreshed. ${allureResponse.data.count || 0} Allure reports updated.`);
      } else {
        await fetchTestsByPlatformAndVersion();
        message.success('Release tests refreshed');
      }
    } catch (error) {
      console.error('Error refreshing all data:', error);
      message.error('Failed to refresh data');
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

      // Record the start time before triggering
      const startTime = new Date().toISOString();

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

      // Update Jenkins job status with the start time
      // This will track the job status using the new API
      // Only update job status if jenkinsSettings is available
      if (jenkinsSettings?.jenkins_url) {
        const jobUrls = [];

        // Collect job URLs for all selected versions
        if (platform === 'android' || !platform || platform?.startsWith('android')) {
          selectedAndroidVersions.forEach(v => {
            jobUrls.push(`${jenkinsSettings.jenkins_url}/job/mobile_test/job/FortiToken_Mobile/job/android/job/${v}/job/${v}_auto_fac_token/`);
          });
        }
        if (platform === 'ios' || !platform || platform?.startsWith('ios')) {
          selectedIosVersions.forEach(v => {
            jobUrls.push(`${jenkinsSettings.jenkins_url}/job/mobile_test/job/FortiToken_Mobile/job/ios/job/${v}/job/${v}_auto_fac_token/`);
          });
        }

        // Update status for each job
        await Promise.all(jobUrls.map(async (jobUrl) => {
          try {
            await axios.post(
              `${API_URL}/api/jenkins/job-status/update`,
              {},
              {
                params: {
                  job_url: jobUrl,
                  timestamp: startTime,
                  job_name: jobUrl.split('/').slice(-2)[0]
                }
              }
            );
          } catch (error) {
            console.error('Failed to update job status for', jobUrl, error);
          }
        }));
      }

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


  const handleDeleteTest = async (testId) => {
    try {
      await axios.delete(`${API_URL}/api/release-tests/${testId}`);
      message.success('Release test deleted successfully');
      fetchTestsByPlatformAndVersion();
    } catch (error) {
      message.error('Failed to delete release test');
    }
  };

  // View test cases for a test
  const handleViewTestCases = async (test) => {
    console.log('=== DEBUG: handleViewTestCases called with test ===', test);

    try {
      // Fetch latest test cases from API
      const response = await axios.get(`${API_URL}/api/release-tests/${test.id}/test-cases`);
      console.log('Test cases API response:', response.data);

      setTestCasesDrawer({
        visible: true,
        testCases: response.data.test_cases || [],
        currentTest: test
      });
    } catch (error) {
      console.error('Failed to fetch test cases:', error);
      message.error('Failed to fetch test cases');
    }
  };

  const handleTestCasesDrawerClose = () => {
    setTestCasesDrawer({ visible: false, testCases: [], currentTest: null });
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
        setModalOpen(false);
        form.resetFields();
        fetchTestsByPlatformAndVersion();
      } else {
        // For create mode, ensure platform and version are set
        values.platform = values.platform || platform;
        values.version = values.version || version;

        // Handle multiple copies creation
        const copyCount = values.copy_count || 1;
        // Remove copy_count from values as it's not needed by the backend
        const { copy_count, ...apiValues } = values;
        let successCount = 0;
        const createdTestIds = [];

        for (let i = 0; i < copyCount; i++) {
          try {
            const response = await axios.post(`${API_URL}/api/release-tests`, apiValues);
            successCount++;
            if (response.data && response.data.id) {
              createdTestIds.push(response.data.id);
            }
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

          // If tests were created, prompt to upload ZIP file
          if (createdTestIds.length > 0) {
            // Ask user if they want to upload ZIP now
            const uploadZip = window.confirm('Test record(s) created. Would you like to upload an Allure ZIP report now?');
            if (uploadZip) {
              // Upload ZIP for each created test
              for (const testId of createdTestIds) {
                await handlePopulateFromZipForTest(testId);
              }
            }
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

  // Helper function to handle ZIP upload for a specific test ID
  const handlePopulateFromZipForTest = async (testId) => {
    return new Promise((resolve, reject) => {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = '.zip';
      fileInput.style.display = 'none';

      fileInput.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) {
          resolve();
          return;
        }

        if (!file.name.endsWith('.zip')) {
          message.error('Please select a ZIP file');
          reject(new Error('Invalid file type'));
          return;
        }

        try {
          const formData = new FormData();
          formData.append('file', file);

          await axios.post(`${API_URL}/api/release-tests/${testId}/upload-zip`, formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          });

          message.success('Release test populated from ZIP file successfully');
          fetchTestsByPlatformAndVersion();
          resolve();
        } catch (error) {
          message.error('Failed to populate release test from ZIP file');
          reject(error);
        }
      };

      document.body.appendChild(fileInput);
      fileInput.click();
      document.body.removeChild(fileInput);
    });
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

      setSaving(true);

      // Extract build number from URL if present (e.g., http://.../64/ -> 64)
      const buildNumberMatch = jenkinsUrl.match(/\/(\d+)\/$/);
      const buildNumber = buildNumberMatch ? parseInt(buildNumberMatch[1]) : null;

      // Call the backend API to populate from Allure
      // Pass the build URL and build number (backend will download allure-report.zip)
      await axios.post(`${API_URL}/api/release-tests/populate-from-allure`, null, {
        params: {
          test_id: editingTest.id,
          build_url: jenkinsUrl.endsWith('/') ? jenkinsUrl : jenkinsUrl + '/',
          build_number: buildNumber
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
        const isSubtask = record.metadata?.is_subtask || record.platform?.includes('_fac_token') ||
                          record.platform?.includes('_fgt_token') ||
                          record.platform?.includes('_ftc_token_on_fac') ||
                          record.platform?.includes('_ftc_token_on_fgt');

        let displayName = platform ? platform.toString().toUpperCase() : 'UNKNOWN';
        let color = 'default';

        if (isSubtask) {
          // Display sub-task name
          const taskName = record.metadata?.task_name || record.metadata?.task_display || '';
          const taskDisplay = record.metadata?.task_display || taskName;
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

        // Use counts from backend (passed_count, failed_count, skipped_count)
        // These are populated from Allure report data
        const passedCount = record.passed_count || 0;
        const failedCount = record.failed_count || 0;
        const skippedCount = record.skipped_count || 0;

        // Debug log to help trace data
        console.log('Results for', record.platform, ':', { passedCount, failedCount, skippedCount, test_cases: record.test_cases });

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
      title: 'Jenkins URL',
      key: 'jenkins_url',
      render: (_, record) => (
        <a href={record.jenkins_build_url || '#'} target="_blank" rel="noopener noreferrer">
          {record.jenkins_build_number ? `Build #${record.jenkins_build_number}` : 'View Build'}
        </a>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => handleViewTestCases(record)}
            title="View test cases"
          >
            Test Cases
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => handleRefreshJobStatus(record)}
            title="Refresh status from Jenkins"
          >
            Refresh
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
              onClick={handleRefreshAll}
              title="Refresh all test data from Jenkins"
            >
              Refresh All
            </Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStartJenkinsTest}
            >
              Start Release Test
            </Button>
            <Button
              danger
              onClick={() => navigate('/release-tests')}
            >
              Back
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
        {/* Test Cases Table */}
        <div style={{ marginBottom: 16 }}>
          <h3>Test Cases</h3>
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
      </Card>


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
      {/* Test Cases Drawer */}
      <Drawer
        title={`Test Cases - ${testCasesDrawer.currentTest?.platform || ''} (${testCasesDrawer.testCases.length} tests)`}
        placement="right"
        width={800}
        open={testCasesDrawer.visible}
        onClose={handleTestCasesDrawerClose}
      >
        {testCasesDrawer.testCases.length > 0 ? (
          <Table
            columns={[
              {
                title: 'Test Name',
                dataIndex: 'name',
                key: 'name',
                render: (text) => <code>{text}</code>,
              },
              {
                title: 'Status',
                dataIndex: 'status',
                key: 'status',
                render: (status) => (
                  <Tag color={
                    status?.toLowerCase()?.includes('pass') ? 'green' :
                    status?.toLowerCase()?.includes('fail') ? 'red' :
                    status?.toLowerCase()?.includes('skip') ? 'orange' : 'default'
                  }>
                    {status?.toUpperCase()}
                  </Tag>
                ),
              },
              {
                title: 'Test Class',
                dataIndex: 'test_class',
                key: 'test_class',
              },
              {
                title: 'Duration (ms)',
                dataIndex: 'duration_ms',
                key: 'duration_ms',
              },
            ]}
            dataSource={testCasesDrawer.testCases}
            rowKey={(record, index) => record.name || index}
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <p>No test cases available</p>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default ReleaseTestDetails;