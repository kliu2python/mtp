import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, Modal, Popconfirm, Row, Select, Space, Table, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

const ReleaseTestsByVersion = () => {
  const [testCycles, setTestCycles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  useEffect(() => {
    fetchTestCycles();
  }, []);

  const fetchTestCycles = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/release-cycles`);
      const cycles = response.data;

      // Fetch test counts for each cycle
      const cyclesWithCounts = await Promise.all(cycles.map(async (cycle) => {
        try {
          const testsResponse = await axios.get(`${API_URL}/api/release-cycles/${cycle.id}/tests`);
          const tests = testsResponse.data;
          const totalTests = tests.length;
          const passedTests = tests.filter(t => t.status === 'passed').length;
          const failedTests = tests.filter(t => t.status === 'failed' || t.status === 'error').length;

          return {
            ...cycle,
            totalTests,
            passedTests,
            failedTests,
            passRate: totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0
          };
        } catch (error) {
          return { ...cycle, totalTests: 0, passedTests: 0, failedTests: 0, passRate: 0 };
        }
      }));

      setTestCycles(cyclesWithCounts);
    } catch (error) {
      message.error('Failed to fetch release test cycles');
    } finally {
      setLoading(false);
    }
  };

  const refreshTestCycles = async () => {
    await fetchTestCycles();
    message.success('Release test cycles refreshed');
  };

  const handleCreateCycle = async (values) => {
    try {
      setCreating(true);
      await axios.post(`${API_URL}/api/release-cycles`, values);
      message.success('Release test cycle created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      fetchTestCycles();
    } catch (error) {
      console.error('Failed to create release test cycle:', error);
      message.error('Failed to create release test cycle: ' + (error.response?.data?.detail || error.message));
    } finally {
      setCreating(false);
    }
  };

  const showCreateModal = () => {
    form.resetFields();
    setCreateModalVisible(true);
  };

  const handleDeleteCycle = async (record) => {
    try {
      await axios.delete(`${API_URL}/api/release-cycles/${record.id}`);
      message.success('Release test cycle deleted successfully');
      fetchTestCycles();
    } catch (error) {
      console.error('Failed to delete release test cycle:', error);
      message.error('Failed to delete release test cycle');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'default';
      case 'running': return 'blue';
      case 'completed': return 'green';
      case 'failed': return 'red';
      default: return 'default';
    }
  };

  const columns = [
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      sorter: (a, b) => a.version.localeCompare(b.version),
    },
    {
      title: 'Project',
      dataIndex: 'project',
      key: 'project',
      render: (project) => {
        const projectMap = {
          'ftm': 'FTM',
          'fortiexplorer': 'FortiExplorer GO',
          'fortiedr': 'FortiEDR Mobile'
        };
        return projectMap[project] || project || 'N/A';
      },
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform) => {
        const color = platform === 'android' ? 'green' : platform === 'ios' ? 'blue' : 'default';
        return <Tag color={color}>{platform?.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{status?.toUpperCase()}</Tag>,
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
      title: 'Pass Rate',
      key: 'passRate',
      render: (_, record) => `${record.passRate}%`,
      sorter: (a, b) => a.passRate - b.passRate,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            onClick={() => navigate(`/release-tests/details/${record.platform}/${record.version}?project=${record.project}`)}
          >
            View Details
          </Button>
          <Popconfirm
            title="Delete Release Test Cycle"
            description={`Are you sure to delete ${record.version} (${record.project})? This will delete all associated test executions.`}
            onConfirm={() => handleDeleteCycle(record)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
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
      <Card
        title="Release Test Cycles"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={showCreateModal}
            >
              New Cycle
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
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 'max-content' }}
        />
      </Card>

      <Modal
        title="Create New Release Test Cycle"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={creating}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateCycle}
          initialValues={{
            project: 'ftm',
            platform: 'all'
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Version"
                name="version"
                rules={[{ required: true, message: 'Please enter version' }]}
              >
                <Input placeholder="e.g., 6.4.0" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="Project"
                name="project"
                rules={[{ required: true, message: 'Please select project' }]}
              >
                <Select>
                  <Option value="ftm">FTM</Option>
                  <Option value="fortiexplorer">FortiExplorer GO</Option>
                  <Option value="fortiedr">FortiEDR Mobile</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Platform"
                name="platform"
                rules={[{ required: true, message: 'Please select platform' }]}
              >
                <Select>
                  <Option value="all">All</Option>
                  <Option value="android">Android</Option>
                  <Option value="ios">iOS</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Description"
                name="description"
              >
                <Input placeholder="Optional description" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default ReleaseTestsByVersion;
