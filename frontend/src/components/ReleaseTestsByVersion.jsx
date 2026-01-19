import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Modal, Row, Select, Space, Table, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';
import { useNavigate } from 'react-router-dom';

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

        // Calculate counts based on actual test cases if available
        if (test.test_cases && Array.isArray(test.test_cases)) {
          const passedCount = test.test_cases.filter(tc => {
            const status = tc.status ? tc.status.toString().toUpperCase() : '';
            return status === 'PASSED';
          }).length;

          const failedCount = test.test_cases.filter(tc => {
            const status = tc.status ? tc.status.toString().toUpperCase() : '';
            return status === 'FAILED' || status === 'BROKEN';
          }).length;

          const skippedCount = test.test_cases.filter(tc => {
            const status = tc.status ? tc.status.toString().toUpperCase() : '';
            return status === 'SKIPPED';
          }).length;

          cycleData.totalTests += passedCount + failedCount + skippedCount;
          cycleData.passedTests += passedCount;
          cycleData.failedTests += failedCount;
          cycleData.skippedTests += skippedCount;
        } else {
          // Fallback to original counter fields if test cases aren't available
          cycleData.totalTests += (test.passed_count || 0) + (test.failed_count || 0) + (test.skipped_count || 0);
          cycleData.passedTests += test.passed_count || 0;
          cycleData.failedTests += test.failed_count || 0;
          cycleData.skippedTests += test.skipped_count || 0;
        }
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
    // Set default values for required fields that aren't shown in the simplified form
    form.setFieldsValue({
      build_number: '',
      test_suite: 'regression',
      test_type: 'critical'
    });
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
              Add Release Test
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
            <Col span={12}>
              <Form.Item
                label="Version"
                name="version"
                rules={[{ required: true, message: 'Please enter version' }]}
              >
                <Input placeholder="e.g., 1.2.3" />
              </Form.Item>
            </Col>
          </Row>

          {/* Hidden fields with default values */}
          <Form.Item
            name="build_number"
            initialValue=""
            hidden
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="test_suite"
            initialValue="regression"
            hidden
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="test_type"
            initialValue="critical"
            hidden
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReleaseTestsByVersion;