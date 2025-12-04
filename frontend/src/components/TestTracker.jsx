import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  message,
  Select,
  Space,
  Typography,
  Divider,
  Tooltip,
  Progress,
  Empty,
  Spin
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  LinkOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { Title, Text } = Typography;

const TestTracker = () => {
  const [vms, setVms] = useState([]);
  const [apks, setApks] = useState([]);
  const [selectedType, setSelectedType] = useState('vm'); // 'vm' or 'apk'
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [testHistory, setTestHistory] = useState([]);
  const [historyPagination, setHistoryPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  });

  useEffect(() => {
    fetchVms();
    fetchApks();
  }, []);

  const fetchVms = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/vms`);
      setVms(response.data.vms || []);
      if (response.data.vms && response.data.vms.length > 0) {
        setSelectedId(response.data.vms[0].id);
        fetchTestData('vm', response.data.vms[0].id);
      }
    } catch (error) {
      message.error('Failed to fetch VMs');
    }
  };

  const fetchApks = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/apks/`);
      setApks(response.data.apk_files || []);
    } catch (error) {
      message.error('Failed to fetch APK/IPA files');
    }
  };

  const fetchTestData = async (type, id, page = 1, pageSize = 20) => {
    if (!id) return;

    setLoading(true);
    try {
      const analyticsEndpoint = type === 'vm'
        ? `${API_URL}/api/tests/analytics/vm/${id}`
        : `${API_URL}/api/tests/analytics/apk/${id}`;

      const historyEndpoint = type === 'vm'
        ? `${API_URL}/api/tests/history/vm/${id}`
        : `${API_URL}/api/tests/history/apk/${id}`;

      const [analyticsRes, historyRes] = await Promise.all([
        axios.get(analyticsEndpoint),
        axios.get(historyEndpoint, {
          params: {
            limit: pageSize,
            offset: (page - 1) * pageSize
          }
        })
      ]);

      setAnalytics(analyticsRes.data);
      setTestHistory(historyRes.data.records || []);
      setHistoryPagination({
        current: page,
        pageSize: pageSize,
        total: historyRes.data.total || 0
      });
    } catch (error) {
      message.error('Failed to fetch test data');
      setAnalytics(null);
      setTestHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const handleTypeChange = (value) => {
    setSelectedType(value);
    setSelectedId(null);
    setAnalytics(null);
    setTestHistory([]);
  };

  const handleSelectionChange = (value) => {
    setSelectedId(value);
    fetchTestData(selectedType, value);
  };

  const handleRefresh = () => {
    if (selectedId) {
      fetchTestData(selectedType, selectedId, historyPagination.current, historyPagination.pageSize);
    }
  };

  const handleTableChange = (pagination) => {
    fetchTestData(selectedType, selectedId, pagination.current, pagination.pageSize);
  };

  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase() || '';
    if (statusLower === 'passed' || statusLower === 'success') return 'success';
    if (statusLower === 'failed' || statusLower === 'error') return 'error';
    return 'default';
  };

  const getStatusIcon = (status) => {
    const statusLower = status?.toLowerCase() || '';
    if (statusLower === 'passed' || statusLower === 'success') return <CheckCircleOutlined />;
    if (statusLower === 'failed' || statusLower === 'error') return <CloseCircleOutlined />;
    return <ClockCircleOutlined />;
  };

  const columns = [
    {
      title: 'Test Suite',
      dataIndex: 'test_suite',
      key: 'test_suite',
      width: 150,
    },
    {
      title: 'Test Case',
      dataIndex: 'test_case',
      key: 'test_case',
      width: 200,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status?.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration) => `${duration?.toFixed(2)}s`,
    },
    {
      title: 'Executed At',
      dataIndex: 'executed_at',
      key: 'executed_at',
      width: 180,
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: 'Jenkins',
      key: 'jenkins',
      width: 120,
      render: (_, record) => {
        if (record.jenkins_build_url) {
          return (
            <Tooltip title="View Jenkins Build">
              <Button
                type="link"
                icon={<LinkOutlined />}
                href={record.jenkins_build_url}
                target="_blank"
                size="small"
              >
                Build #{record.jenkins_build_number}
              </Button>
            </Tooltip>
          );
        }
        return <Text type="secondary">N/A</Text>;
      },
    },
    {
      title: 'Error',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: {
        showTitle: false,
      },
      render: (error) => (
        error ? (
          <Tooltip title={error}>
            <Text type="danger" ellipsis>{error}</Text>
          </Tooltip>
        ) : '-'
      ),
    },
  ];

  const getSelectedName = () => {
    if (!selectedId) return 'None';
    if (selectedType === 'vm') {
      const vm = vms.find(v => v.id === selectedId);
      return vm ? vm.name : 'Unknown';
    } else {
      const apk = apks.find(a => a.id === selectedId);
      return apk ? apk.display_name : 'Unknown';
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0 }}>Test Tracker</Title>
        <Space>
          <Select
            value={selectedType}
            onChange={handleTypeChange}
            style={{ width: 150 }}
            options={[
              { label: 'Virtual Machine', value: 'vm' },
              { label: 'APK/IPA File', value: 'apk' }
            ]}
          />
          <Select
            value={selectedId}
            onChange={handleSelectionChange}
            style={{ width: 300 }}
            placeholder={`Select ${selectedType === 'vm' ? 'VM' : 'APK/IPA'}`}
            showSearch
            filterOption={(input, option) =>
              option.label.toLowerCase().includes(input.toLowerCase())
            }
            options={
              selectedType === 'vm'
                ? vms.map(vm => ({ label: vm.name, value: vm.id }))
                : apks.map(apk => ({
                    label: `${apk.display_name} - v${apk.version_name || 'N/A'}`,
                    value: apk.id
                  }))
            }
          />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            Refresh
          </Button>
        </Space>
      </div>

      {!selectedId ? (
        <Empty description={`Please select a ${selectedType === 'vm' ? 'VM' : 'APK/IPA file'} to view test history`} />
      ) : loading && !analytics ? (
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* Analytics Section */}
          {analytics && (
            <>
              <Card title={`Test Analytics - ${getSelectedName()}`} style={{ marginBottom: 24 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="Total Tests"
                      value={analytics.total_tests}
                      prefix={<BarChartOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="Passed Tests"
                      value={analytics.passed_tests}
                      valueStyle={{ color: '#3f8600' }}
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="Failed Tests"
                      value={analytics.failed_tests}
                      valueStyle={{ color: '#cf1322' }}
                      prefix={<CloseCircleOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Pass Rate"
                        value={analytics.pass_rate}
                        suffix="%"
                        valueStyle={{ color: analytics.pass_rate >= 80 ? '#3f8600' : '#cf1322' }}
                      />
                      <Progress
                        percent={analytics.pass_rate}
                        status={analytics.pass_rate >= 80 ? 'success' : 'exception'}
                        showInfo={false}
                      />
                    </Card>
                  </Col>
                </Row>

                <Divider />

                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="Test Suites" size="small">
                      {analytics.test_suites && analytics.test_suites.length > 0 ? (
                        analytics.test_suites.map((suite, index) => (
                          <div key={index} style={{ marginBottom: 12 }}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <Text strong>{suite.name}</Text>
                              <Space>
                                <Tag color="success">{suite.passed} Passed</Tag>
                                <Tag color="error">{suite.failed} Failed</Tag>
                                <Tag>Total: {suite.total}</Tag>
                                <Text type="secondary">Pass Rate: {suite.pass_rate.toFixed(2)}%</Text>
                              </Space>
                              <Progress
                                percent={suite.pass_rate}
                                status={suite.pass_rate >= 80 ? 'success' : 'exception'}
                                size="small"
                              />
                            </Space>
                          </div>
                        ))
                      ) : (
                        <Empty description="No test suites" />
                      )}
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="Recent Failures" size="small">
                      {analytics.recent_failures && analytics.recent_failures.length > 0 ? (
                        <div style={{ maxHeight: 300, overflow: 'auto' }}>
                          {analytics.recent_failures.map((failure, index) => (
                            <Card key={index} size="small" style={{ marginBottom: 8 }}>
                              <Text strong>{failure.test_case}</Text>
                              <br />
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {new Date(failure.executed_at).toLocaleString()}
                              </Text>
                              {failure.error_message && (
                                <>
                                  <br />
                                  <Text type="danger" ellipsis style={{ fontSize: 12 }}>
                                    {failure.error_message}
                                  </Text>
                                </>
                              )}
                            </Card>
                          ))}
                        </div>
                      ) : (
                        <Empty description="No recent failures" />
                      )}
                    </Card>
                  </Col>
                </Row>

                <Divider />

                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="Average Duration"
                      value={analytics.average_duration}
                      suffix="seconds"
                      precision={2}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Last Test Date"
                      value={analytics.last_test_date ? new Date(analytics.last_test_date).toLocaleString() : 'Never'}
                    />
                  </Col>
                  {selectedType === 'apk' && analytics.vms_tested && (
                    <Col span={8}>
                      <Statistic
                        title="VMs Tested"
                        value={analytics.vms_tested.length}
                      />
                    </Col>
                  )}
                </Row>
              </Card>

              {/* Test History Section */}
              <Card title="Test History">
                <Table
                  dataSource={testHistory}
                  columns={columns}
                  rowKey="id"
                  loading={loading}
                  pagination={{
                    ...historyPagination,
                    showSizeChanger: true,
                    showTotal: (total) => `Total ${total} test records`,
                  }}
                  onChange={handleTableChange}
                  scroll={{ x: 1200 }}
                />
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
};

export default TestTracker;
