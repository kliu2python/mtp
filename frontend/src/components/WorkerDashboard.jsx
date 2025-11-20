import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Progress,
  Alert,
  Space,
  Button,
  Tooltip,
  Badge,
  List,
  Typography,
  Divider,
  Timeline,
  Empty,
  Spin
} from 'antd';
import {
  ClusterOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  ApiOutlined,
  ReloadOutlined,
  StopOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;

const API_URL = import.meta.env.VITE_API_URL || '';

const WorkerDashboard = () => {
  const [overview, setOverview] = useState(null);
  const [runningTests, setRunningTests] = useState([]);
  const [queuedTests, setQueuedTests] = useState([]);
  const [recentTests, setRecentTests] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 5 seconds if enabled
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchDashboardData, 5000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const fetchDashboardData = async () => {
    try {
      const [overviewRes, runningRes, queueRes, recentRes, alertsRes] = await Promise.all([
        axios.get(`${API_URL}/api/dashboard/overview`),
        axios.get(`${API_URL}/api/dashboard/tests/running`),
        axios.get(`${API_URL}/api/dashboard/tests/queue`),
        axios.get(`${API_URL}/api/dashboard/tests/recent?limit=10`),
        axios.get(`${API_URL}/api/dashboard/alerts`)
      ]);

      setOverview(overviewRes.data);
      setRunningTests(runningRes.data.tests || []);
      setQueuedTests(queueRes.data.tests || []);
      setRecentTests(recentRes.data.tests || []);
      setAlerts(alertsRes.data.alerts || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setLoading(false);
    }
  };

  const performNodeAction = async (nodeId, action) => {
    try {
      await axios.post(`${API_URL}/api/dashboard/nodes/${nodeId}/action?action=${action}`);
      fetchDashboardData();
    } catch (error) {
      console.error(`Failed to ${action} node:`, error);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'ONLINE': 'success',
      'BUSY': 'processing',
      'OFFLINE': 'default',
      'ERROR': 'error',
      'TESTING': 'warning'
    };
    return colors[status] || 'default';
  };

  const getTestStatusColor = (status) => {
    const colors = {
      'queued': 'default',
      'running': 'processing',
      'completed': 'success',
      'failed': 'error'
    };
    return colors[status] || 'default';
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  const nodeColumns = [
    {
      title: 'Node Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <Badge status={getStatusColor(record.status)} />
          <Text strong>{text}</Text>
        </Space>
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getStatusColor(status)}>{status}</Tag>
    },
    {
      title: 'Executors',
      key: 'executors',
      render: (_, record) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text>{record.current_executors} / {record.max_executors}</Text>
          <Progress
            percent={record.utilization}
            size="small"
            status={record.utilization > 90 ? 'exception' : 'active'}
          />
        </Space>
      )
    },
    {
      title: 'Running Tests',
      dataIndex: 'running_tests',
      key: 'running_tests',
      render: (count) => (
        <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />
      )
    },
    {
      title: 'Resources',
      key: 'resources',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Tooltip title="CPU Usage">
            <Text type="secondary">CPU: {record.metrics?.cpu_usage?.toFixed(1)}%</Text>
          </Tooltip>
          <Tooltip title="Memory Usage">
            <Text type="secondary">MEM: {record.metrics?.memory_usage?.toFixed(1)}%</Text>
          </Tooltip>
        </Space>
      )
    },
    {
      title: 'Performance',
      key: 'performance',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text type="secondary">Tests: {record.metrics?.total_tests || 0}</Text>
          <Text type={record.metrics?.pass_rate > 80 ? 'success' : 'warning'}>
            Pass Rate: {record.metrics?.pass_rate?.toFixed(1)}%
          </Text>
        </Space>
      )
    },
    {
      title: 'Labels',
      dataIndex: 'labels',
      key: 'labels',
      render: (labels) => (
        <>
          {labels?.slice(0, 2).map(label => (
            <Tag key={label} color="blue" style={{ marginBottom: 4 }}>{label}</Tag>
          ))}
          {labels?.length > 2 && (
            <Tooltip title={labels.slice(2).join(', ')}>
              <Tag>+{labels.length - 2}</Tag>
            </Tooltip>
          )}
        </>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="Ping Node">
            <Button
              size="small"
              icon={<ApiOutlined />}
              onClick={() => performNodeAction(record.id, 'ping')}
            />
          </Tooltip>
          <Tooltip title={record.status === 'OFFLINE' ? 'Enable' : 'Disable'}>
            <Button
              size="small"
              icon={record.status === 'OFFLINE' ? <PlayCircleOutlined /> : <StopOutlined />}
              onClick={() => performNodeAction(record.id, record.status === 'OFFLINE' ? 'enable' : 'disable')}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  const testColumns = [
    {
      title: 'Task ID',
      dataIndex: 'task_id',
      key: 'task_id',
      render: (id) => (
        <Tooltip title={id}>
          <Text code>{id?.substring(0, 8)}</Text>
        </Tooltip>
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={getTestStatusColor(status)}>{status}</Tag>
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress) => (
        <Progress
          percent={progress}
          size="small"
          status={progress === 100 ? 'success' : 'active'}
        />
      )
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration) => <Text>{formatDuration(duration)}</Text>
    },
    {
      title: 'Node',
      dataIndex: 'node_id',
      key: 'node_id',
      render: (nodeId) => {
        const node = overview?.node_details?.find(n => n.id === nodeId);
        return node ? <Tag>{node.name}</Tag> : <Text type="secondary">N/A</Text>;
      }
    }
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" tip="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>
            <ClusterOutlined /> Worker Node Dashboard
          </Title>
        </Col>
        <Col>
          <Space>
            <Text type="secondary">Auto-refresh: </Text>
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              icon={<SyncOutlined />}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? 'ON' : 'OFF'}
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchDashboardData}
            >
              Refresh Now
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Alert
          message={`${alerts.length} Active Alert${alerts.length > 1 ? 's' : ''}`}
          description={
            <List
              size="small"
              dataSource={alerts.slice(0, 3)}
              renderItem={(alert) => (
                <List.Item>
                  <Space>
                    {alert.severity === 'error' ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> : <WarningOutlined style={{ color: '#faad14' }} />}
                    <Text>{alert.message}</Text>
                  </Space>
                </List.Item>
              )}
            />
          }
          type={alerts.some(a => a.severity === 'error') ? 'error' : 'warning'}
          closable
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Nodes"
              value={overview?.nodes?.total || 0}
              prefix={<ClusterOutlined />}
              suffix={
                <Text type="secondary" style={{ fontSize: 14 }}>
                  ({overview?.nodes?.online || 0} online)
                </Text>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Executor Utilization"
              value={overview?.executors?.utilization?.toFixed(1) || 0}
              suffix="%"
              prefix={<ThunderboltOutlined />}
              valueStyle={{
                color: overview?.executors?.utilization > 80 ? '#cf1322' : '#3f8600'
              }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {overview?.executors?.active || 0} / {overview?.executors?.total || 0} active
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Running Tests"
              value={overview?.tests?.running || 0}
              prefix={<PlayCircleOutlined style={{ color: '#1890ff' }} />}
              suffix={
                overview?.tests?.queued > 0 ? (
                  <Text type="secondary" style={{ fontSize: 14 }}>
                    (+{overview?.tests?.queued} queued)
                  </Text>
                ) : null
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Success Rate (Today)"
              value={overview?.tests?.success_rate || 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{
                color: overview?.tests?.success_rate > 80 ? '#3f8600' : '#cf1322'
              }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {overview?.tests?.completed_today || 0} passed / {overview?.tests?.total_today || 0} total
            </Text>
          </Card>
        </Col>
      </Row>

      {/* Worker Nodes Table */}
      <Card
        title={<><ClusterOutlined /> Worker Nodes</>}
        style={{ marginBottom: 24 }}
        extra={
          <Space>
            <Badge
              status="success"
              text={`${overview?.nodes?.online || 0} Online`}
            />
            <Badge
              status="processing"
              text={`${overview?.nodes?.busy || 0} Busy`}
            />
            <Badge
              status="default"
              text={`${overview?.nodes?.offline || 0} Offline`}
            />
          </Space>
        }
      >
        <Table
          dataSource={overview?.node_details || []}
          columns={nodeColumns}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      </Card>

      {/* Running and Queued Tests */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <PlayCircleOutlined style={{ color: '#1890ff' }} />
                <Text>Running Tests ({runningTests.length})</Text>
              </Space>
            }
          >
            {runningTests.length > 0 ? (
              <Table
                dataSource={runningTests}
                columns={testColumns}
                rowKey="task_id"
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="No tests currently running" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ClockCircleOutlined style={{ color: '#faad14' }} />
                <Text>Queued Tests ({queuedTests.length})</Text>
              </Space>
            }
          >
            {queuedTests.length > 0 ? (
              <List
                dataSource={queuedTests}
                renderItem={(test) => (
                  <List.Item>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text code>{test.task_id?.substring(0, 8)}</Text>
                      <Tag color="default">{test.status}</Tag>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="No tests in queue" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Recent Test History */}
      <Card
        title={<><ClockCircleOutlined /> Recent Test History</>}
        style={{ marginTop: 24 }}
      >
        {recentTests.length > 0 ? (
          <Timeline>
            {recentTests.slice(0, 10).map((test) => (
              <Timeline.Item
                key={test.task_id}
                color={test.status === 'completed' ? 'green' : 'red'}
                dot={
                  test.status === 'completed' ?
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                }
              >
                <Space direction="vertical" size="small">
                  <Space>
                    <Text code>{test.task_id?.substring(0, 8)}</Text>
                    <Tag color={getTestStatusColor(test.status)}>{test.status}</Tag>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Duration: {formatDuration(test.duration)}
                  </Text>
                </Space>
              </Timeline.Item>
            ))}
          </Timeline>
        ) : (
          <Empty description="No recent test history" />
        )}
      </Card>
    </div>
  );
};

export default WorkerDashboard;
