import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Descriptions, Form, Input, Modal, Row, Select, Space, Table, Tag, message } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const ReleaseTestDetails = () => {
  const { platform, version } = useParams();
  const navigate = useNavigate();
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // create, edit, or view
  const [editingTest, setEditingTest] = useState(null);
  const [viewingTest, setViewingTest] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

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

      console.log('=== DEBUG: Fetching release tests with params ===', params);
      const response = await axios.get(`${API_URL}/api/release-tests`, {
        params: params
      });
      console.log('=== DEBUG: Received release tests data ===', response.data);

      // Log test cases info for each test
      response.data.forEach((test, index) => {
        console.log(`Test ${index} (${test.build_number}):`, {
          hasTestCasesDirect: !!test.test_cases,
          testCasesCount: test.test_cases ? test.test_cases.length : 0,
          hasTestCasesInMetadata: !!(test.metadata && test.metadata.test_cases),
          metadataTestCasesCount: test.metadata && test.metadata.test_cases ? test.metadata.test_cases.length : 0
        });
      });

      setTests(response.data);
      setLoading(false);
    } catch (error) {
      console.log('=== DEBUG: Error fetching release tests ===', error);
      message.error('Failed to fetch release tests');
      setLoading(false);
    }
  };

  const refreshTests = async () => {
    try {
      setLoading(true);
      await fetchTestsByPlatformAndVersion();
      message.success('Release tests refreshed');
    } catch (error) {
      message.error('Failed to refresh release tests');
      setLoading(false);
    }
  };

  const handleCreateTest = () => {
    form.resetFields();
    form.setFieldsValue({
      platform: platform,
      version: version
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
        await axios.post(`${API_URL}/api/release-tests`, values);
        message.success('Release test created successfully');
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
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform) => {
        const color = platform === 'android' ? 'green' : platform === 'ios' ? 'blue' : 'default';
        return <Tag color={color}>{platform?.toUpperCase()}</Tag>;
      },
      filters: [
        { text: 'Android', value: 'android' },
        { text: 'iOS', value: 'ios' }
      ],
      onFilter: (value, record) => record.platform === value,
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
      render: (status) => <Tag color={getStatusColor(status)}>{status?.toUpperCase()}</Tag>,
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
        title={`Release Tests${platform ? ` - ${platform.toUpperCase()}` : ''}${version ? ` - Version ${version}` : ''}`}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={refreshTests}
              loading={loading}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateTest}
            >
              Add Release Test
            </Button>
            <Button
              onClick={() => navigate('/release-tests')}
            >
              Back to Platforms
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={tests}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 'max-content' }}
        />
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
          </Row>

          <Row gutter={16}>
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
          </Row>
        </Form>
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
      </Modal>
    </div>
  );
};

export default ReleaseTestDetails;