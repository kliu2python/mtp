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
  const [releaseTestConfig, setReleaseTestConfig] = useState({
    versions: [],
    build_numbers: [],
    version_build_numbers: []
  });
  const [configLoading, setConfigLoading] = useState(false);
  const navigate = useNavigate();

  // Get available build numbers based on selected version and platform
  const getAvailableBuildNumbers = (version, platform) => {
    const versionRanges = releaseTestConfig.version_build_numbers || [];

    if (platform === 'android') {
      const range = versionRanges.find(r => r.version === version && r.platform === 'android');
      if (!range) return [];

      const min = range.min_build_number || '';
      const max = range.max_build_number || '';
      if (!min || !max) return [];

      // Generate build numbers between min and max
      const minNum = parseInt(min, 10);
      const maxNum = parseInt(max, 10);
      const result = [];
      for (let i = minNum; i <= maxNum; i++) {
        result.push(i.toString().padStart(4, '0'));
      }
      return result;
    } else if (platform === 'ios') {
      const range = versionRanges.find(r => r.version === version && r.platform === 'ios');
      if (!range) return [];

      // iOS uses the same min_build_number and max_build_number fields
      const min = range.min_build_number || '';
      const max = range.max_build_number || '';
      if (!min || !max) return [];

      const minNum = parseInt(min, 10);
      const maxNum = parseInt(max, 10);
      const result = [];
      for (let i = minNum; i <= maxNum; i++) {
        result.push(i.toString().padStart(4, '0'));
      }
      return result;
    }

    return [];
  };

  // Get version display label (e.g., "6.4.0" from "android_6.4.0")
  const getVersionLabel = (versionStr) => {
    // Remove platform prefix (android_/ios_) and return just the version number
    return versionStr.replace(/^(android_|ios_)/, '');
  };

  // Default versions when config is not set
  const defaultVersions = [
    'android_15', 'android_14', 'android_13', 'android_12', 'android_11', 'android_10',
    'ios_26', 'ios_18', 'ios_17', 'ios_16', 'ios_15'
  ];

  // Fetch release test config
  const fetchReleaseTestConfig = async () => {
    try {
      setConfigLoading(true);
      const response = await axios.get(`${API_URL}/api/release-test-config`);
      const config = response.data;
      console.log('Release test config loaded:', config);
      setReleaseTestConfig({
        versions: config.versions || [],
        build_numbers: config.build_numbers || [],
        version_build_numbers: config.version_build_numbers || []
      });
    } catch (error) {
      console.error('Failed to fetch release test config:', error);
      setReleaseTestConfig({ versions: [], build_numbers: [], version_build_numbers: [] });
    } finally {
      setConfigLoading(false);
    }
  };

  // Get unique version numbers from config (remove duplicates like android_6.4.0 and ios_6.4.0)
  const getVersionOptions = () => {
    // First, try to get versions from version_build_numbers config
    const versionBuildNumbers = releaseTestConfig.version_build_numbers || [];
    if (versionBuildNumbers.length > 0) {
      // Extract unique version numbers from version_build_numbers
      const versionSet = new Set();
      versionBuildNumbers.forEach(vbn => {
        if (vbn.version) {
          versionSet.add(vbn.version);
        }
      });
      return Array.from(versionSet).map(v => ({ label: v, value: v })).sort((a, b) => b.label.localeCompare(a.label));
    }

    // Fall back to versions from config
    const versionsToUse = releaseTestConfig.versions && releaseTestConfig.versions.length > 0
      ? releaseTestConfig.versions
      : defaultVersions;

    const versionSet = new Set();
    const options = [];

    versionsToUse.forEach(v => {
      const versionNum = getVersionLabel(v);
      if (!versionSet.has(versionNum)) {
        versionSet.add(versionNum);
        options.push({ label: versionNum, value: versionNum });
      }
    });

    return options.sort((a, b) => b.label.localeCompare(a.label));
  };

  useEffect(() => {
    fetchTestCycles();
    fetchReleaseTestConfig();
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

          // Count passed and failed (including broken) tests
          const passedTests = tests.filter(t => t.status === 'passed').length;
          const failedTests = tests.filter(t => t.status === 'failed' || t.status === 'error' || t.status === 'broken').length;
          const totalTests = tests.length;

          // Calculate Total Test Cases (sum of passed + failed + broken + skipped)
          let totalTestCases = 0;
          tests.forEach(t => {
            totalTestCases += (t.passed_count || 0) + (t.failed_count || 0) + (t.broken_count || 0) + (t.skipped_count || 0);
          });

          // Calculate unique build numbers for this cycle + platform
          const uniqueBuildNumbers = new Set(tests.map(t => t.build_number)).size;

          return {
            ...cycle,
            totalTests,
            passedTests,
            failedTests,
            passRate: totalTests > 0 ? Math.round((passedTests / totalTests) * 100) : 0,
            totalTestCases,
            uniqueBuilds: uniqueBuildNumbers
          };
        } catch (error) {
          return { ...cycle, totalTests: 0, passedTests: 0, failedTests: 0, passRate: 0, totalTestCases: 0, uniqueBuilds: 0 };
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
      title: 'Total Builds',
      dataIndex: 'uniqueBuilds',
      key: 'uniqueBuilds',
      sorter: (a, b) => a.uniqueBuilds - b.uniqueBuilds,
      render: (builds) => <Tag color="blue">{builds}</Tag>,
    },
    {
      title: 'Total Test Cases',
      key: 'totalTestCases',
      render: (_, record) => <Tag color="green">{record.totalTestCases || 0}</Tag>,
      sorter: (a, b) => (a.totalTestCases || 0) - (b.totalTestCases || 0),
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
            platform: 'android'
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Version"
                name="version"
                rules={[{ required: true, message: 'Please select version' }]}
              >
                <Select
                  placeholder={configLoading ? "Loading..." : "Select version"}
                  loading={configLoading}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={getVersionOptions()}
                />
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
