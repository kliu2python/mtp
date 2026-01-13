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

const { TextArea } = Input;

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

      const response = await axios.get(`${API_URL}/api/release-tests`, {
        params: params
      });
      setTests(response.data);
      setLoading(false);
    } catch (error) {
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
    setModalMode('create');
    setEditingTest(null);
    setModalOpen(true);
  };

  const handleEditTest = (test) => {
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
      apk_file_id: test.apk_file_id,
      test_metadata: test.metadata,
      notes: test.notes
    });
    setModalMode('edit');
    setEditingTest(test);
    setModalOpen(true);
  };

  const handleViewTest = (test) => {
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
      apk_file_id: test.apk_file_id,
      test_metadata: test.metadata,
      notes: test.notes
    });
    setModalMode('view');
    setViewingTest(test);
    setModalOpen(true);
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
      title: 'Started At',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date) => date ? new Date(date).toLocaleString() : 'N/A',
      sorter: (a, b) => new Date(a.started_at) - new Date(b.started_at),
    },
    {
      title: 'Duration (s)',
      dataIndex: 'duration',
      key: 'duration',
      sorter: (a, b) => a.duration - b.duration,
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
      ),
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
              Add Test
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
                <Select placeholder="Select platform" disabled={modalMode === 'view'}>
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
                <Input placeholder="e.g., 1.2.3" disabled={modalMode === 'view'} defaultValue={version} />
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

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Started At"
                name="started_at"
              >
                <Input type="datetime-local" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Completed At"
                name="completed_at"
              >
                <Input type="datetime-local" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="Duration (s)"
                name="duration"
              >
                <Input type="number" placeholder="Duration in seconds" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Passed Count"
                name="passed_count"
              >
                <Input type="number" placeholder="Number of passed tests" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Failed Count"
                name="failed_count"
              >
                <Input type="number" placeholder="Number of failed tests" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Jenkins Job Name"
            name="jenkins_job_name"
          >
            <Input placeholder="Jenkins job name" disabled={modalMode === 'view'} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Jenkins Build Number"
                name="jenkins_build_number"
              >
                <Input type="number" placeholder="Build number" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="APK File ID"
                name="apk_file_id"
              >
                <Input placeholder="UUID of associated APK file" disabled={modalMode === 'view'} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Jenkins Build URL"
            name="jenkins_build_url"
          >
            <Input placeholder="Full URL to Jenkins build" disabled={modalMode === 'view'} />
          </Form.Item>

          <Form.Item
            label="Metadata"
            name="test_metadata"
          >
            <TextArea placeholder='{"key": "value"}' rows={4} disabled={modalMode === 'view'} />
          </Form.Item>

          <Form.Item
            label="Notes"
            name="notes"
          >
            <TextArea placeholder="Additional notes about this test" rows={4} disabled={modalMode === 'view'} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReleaseTestDetails;