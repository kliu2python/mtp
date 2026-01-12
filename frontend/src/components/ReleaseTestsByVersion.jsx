import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Modal, Row, Select, Space, Table, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';
import { useNavigate } from 'react-router-dom';

const { TextArea } = Input;

const ReleaseTestsByVersion = () => {
  const [testCycles, setTestCycles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    fetchTestCycles();
  }, []);

  const fetchTestCycles = async () => {
    try {
      setLoading(true);
      // Fetch all tests to group by platform + version combinations
      const response = await axios.get(`${API_URL}/api/release-tests`);
      const tests = response.data;

      // Group tests by platform + version combination
      const cycleMap = {};
      tests.forEach(test => {
        const platform = test.platform || 'Unknown';
        const version = test.version || 'Unknown';
        const key = `${platform}-${version}`;

        if (!cycleMap[key]) {
          cycleMap[key] = {
            key: key,
            platform: platform,
            version: version,
            totalBuilds: 0,
            passedBuilds: 0,
            totalTests: 0,
            passedTests: 0,
            failedTests: 0,
            skippedTests: 0,
            tests: []
          };
        }

        const cycleData = cycleMap[key];
        cycleData.totalBuilds++;
        cycleData.tests.push(test);

        if (test.status === 'passed') {
          cycleData.passedBuilds++;
        }

        cycleData.totalTests += (test.passed_count || 0) + (test.failed_count || 0) + (test.skipped_count || 0);
        cycleData.passedTests += test.passed_count || 0;
        cycleData.failedTests += test.failed_count || 0;
        cycleData.skippedTests += test.skipped_count || 0;
      });

      // Convert to array format and calculate pass rates
      const cycleArray = Object.values(cycleMap).map(cycleData => {
        const buildPassRate = cycleData.totalBuilds > 0
          ? Math.round((cycleData.passedBuilds / cycleData.totalBuilds) * 100)
          : 0;

        const testPassRate = cycleData.totalTests > 0
          ? Math.round((cycleData.passedTests / cycleData.totalTests) * 100)
          : 0;

        return {
          ...cycleData,
          buildPassRate,
          testPassRate
        };
      });

      setTestCycles(cycleArray);
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch release test cycles');
      setLoading(false);
    }
  };

  const refreshTestCycles = async () => {
    try {
      setLoading(true);
      await fetchTestCycles();
      message.success('Release test cycles refreshed');
    } catch (error) {
      message.error('Failed to refresh release test cycles');
      setLoading(false);
    }
  };

  const handleCreateTest = () => {
    form.resetFields();
    setModalOpen(true);
  };

  const handleSaveTest = async () => {
    try {
      const values = await form.validateFields();

      setSaving(true);

      await axios.post(`${API_URL}/api/release-tests`, values);
      message.success('Release test created successfully');

      setModalOpen(false);
      form.resetFields();
      fetchTestCycles();
    } catch (error) {
      console.error('Failed to create release test:', error);
      message.error('Failed to create release test: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const getPlatformColor = (platform) => {
    switch (platform) {
      case 'android': return 'green';
      case 'ios': return 'blue';
      default: return 'default';
    }
  };

  const columns = [
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform) => {
        const color = getPlatformColor(platform);
        return <Tag color={color}>{platform?.toUpperCase()}</Tag>;
      },
      sorter: (a, b) => a.platform.localeCompare(b.platform),
      filters: [
        { text: 'Android', value: 'android' },
        { text: 'iOS', value: 'ios' }
      ],
      onFilter: (value, record) => record.platform === value,
    },
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      sorter: (a, b) => a.version.localeCompare(b.version),
    },
    {
      title: 'Total Builds',
      dataIndex: 'totalBuilds',
      key: 'totalBuilds',
      sorter: (a, b) => a.totalBuilds - b.totalBuilds,
    },
    {
      title: 'Passed Builds',
      dataIndex: 'passedBuilds',
      key: 'passedBuilds',
      sorter: (a, b) => a.passedBuilds - b.passedBuilds,
    },
    {
      title: 'Build Pass Rate',
      dataIndex: 'buildPassRate',
      key: 'buildPassRate',
      render: (rate) => `${rate}%`,
      sorter: (a, b) => a.buildPassRate - b.buildPassRate,
    },
    {
      title: 'Total Tests',
      dataIndex: 'totalTests',
      key: 'totalTests',
      sorter: (a, b) => a.totalTests - b.totalTests,
    },
    {
      title: 'Passed Tests',
      dataIndex: 'passedTests',
      key: 'passedTests',
      sorter: (a, b) => a.passedTests - b.passedTests,
    },
    {
      title: 'Failed Tests',
      dataIndex: 'failedTests',
      key: 'failedTests',
      sorter: (a, b) => a.failedTests - b.failedTests,
    },
    {
      title: 'Test Pass Rate',
      dataIndex: 'testPassRate',
      key: 'testPassRate',
      render: (rate) => `${rate}%`,
      sorter: (a, b) => a.testPassRate - b.testPassRate,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          onClick={() => navigate(`/release-tests/details/${record.platform}/${record.version}`)}
        >
          View Details
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="Release Test Cycles"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateTest}
            >
              Add Test Result
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={refreshTestCycles}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={testCycles}
          columns={columns}
          rowKey="key"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 'max-content' }}
        />
      </Card>

      {/* Create Test Modal */}
      <Modal
        title="Add New Release Test"
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        onOk={handleSaveTest}
        okText="Save"
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
                <Input placeholder="e.g., 1.2.3-rc1" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Platform"
                name="platform"
                rules={[{ required: true, message: 'Please select platform' }]}
              >
                <Select placeholder="Select platform">
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
                <Input placeholder="e.g., 1.2.3" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Test Suite"
                name="test_suite"
                rules={[{ required: true, message: 'Please enter test suite' }]}
              >
                <Select placeholder="Select test suite">
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
                <Select placeholder="Select test type">
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
                <Select placeholder="Select status">
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
                <Input type="datetime-local" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Completed At"
                name="completed_at"
              >
                <Input type="datetime-local" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="Duration (s)"
                name="duration"
              >
                <Input type="number" placeholder="Duration in seconds" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Passed Count"
                name="passed_count"
              >
                <Input type="number" placeholder="Number of passed tests" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Failed Count"
                name="failed_count"
              >
                <Input type="number" placeholder="Number of failed tests" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Jenkins Job Name"
            name="jenkins_job_name"
          >
            <Input placeholder="Jenkins job name" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Jenkins Build Number"
                name="jenkins_build_number"
              >
                <Input type="number" placeholder="Build number" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="APK File ID"
                name="apk_file_id"
              >
                <Input placeholder="UUID of associated APK file" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Jenkins Build URL"
            name="jenkins_build_url"
          >
            <Input placeholder="Full URL to Jenkins build" />
          </Form.Item>

          <Form.Item
            label="Metadata"
            name="test_metadata"
          >
            <TextArea placeholder='{"key": "value"}' rows={4} />
          </Form.Item>

          <Form.Item
            label="Notes"
            name="notes"
          >
            <TextArea placeholder="Additional notes about this test" rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReleaseTestsByVersion;