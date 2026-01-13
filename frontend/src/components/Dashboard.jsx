import React, { useEffect, useState } from 'react';
import {
  Card,
  Col,
  Divider,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
  message
} from 'antd';
import {
  BugOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  MobileOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { Text } = Typography;

const Dashboard = () => {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    const [vmsRes, devicesRes, mantisRes] = await Promise.allSettled([
      axios.get(`${API_URL}/api/vms/stats/summary`),
      axios.get(`${API_URL}/api/devices/stats/summary`),
      axios.get(`${API_URL}/api/mantis/`, { params: { page: 1, page_size: 1 } })
    ]);

    const nextStats = {};

    if (vmsRes.status === 'fulfilled') {
      nextStats.vms = vmsRes.value.data;
    } else {
      message.error('Failed to fetch VM statistics');
    }

    if (devicesRes.status === 'fulfilled') {
      nextStats.devices = devicesRes.value.data;
    } else {
      message.error('Failed to fetch device statistics');
    }

    if (mantisRes.status === 'fulfilled') {
      nextStats.mantis = mantisRes.value.data;
    }

    setStats(nextStats);
    setLoading(false);
  };

  if (loading) return <div>Loading...</div>;

  const totalVms = stats?.vms?.vms?.total || 0;
  const runningVms = stats?.vms?.vms?.running || 0;
  const testingVms = stats?.vms?.vms?.testing || 0;
  const availableTestbeds = Math.max(totalVms - testingVms, 0);
  const stoppedVms = Math.max(totalVms - runningVms - testingVms, 0);

  const totalDevices = stats?.devices?.total || 0;
  const availableDevices = stats?.devices?.by_status?.available || 0;
  const busyDevices = stats?.devices?.by_status?.busy || 0;

  const tests24h = stats?.vms?.tests_24h;
  const mantisTotal = stats?.mantis?.total || 0;
  const mantisOpen = stats?.mantis?.status_counts?.open || stats?.mantis?.status_counts?.opened || 0;
  const mantisResolved = stats?.mantis?.status_counts?.resolved || 0;
  const mantisClosed = stats?.mantis?.status_counts?.closed || 0;

  return (
    <div>
      <h1>Dashboard</h1>
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Available Testbeds"
              value={availableTestbeds}
              prefix={<CloudServerOutlined />}
            />
            <Text type="secondary">{runningVms} running / {testingVms} testing</Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Running Tests"
              value={testingVms}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
            <Text type="secondary">Linked to active testbeds</Text>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Lab Devices Available"
              value={availableDevices}
              prefix={<MobileOutlined />}
            />
            <Text type="secondary">{busyDevices} busy / {totalDevices} total</Text>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="Test Activity (last 24h)" extra={<Tag color="blue">{tests24h?.total || 0} runs</Tag>}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="Pass Rate"
                  value={tests24h?.pass_rate || 0}
                  suffix="%"
                  valueStyle={{ color: (tests24h?.pass_rate || 0) > 80 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={8}>
                <Statistic title="Passed" value={tests24h?.passed || 0} prefix={<CheckCircleOutlined />} />
              </Col>
              <Col span={8}>
                <Statistic title="Failed" value={tests24h?.failed || 0} prefix={<BugOutlined />} />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Mantis Overview" extra={<Tag color="purple">{mantisTotal} issues</Tag>}>
            <Space size={16} wrap>
              <Statistic title="Open" value={mantisOpen} prefix={<BugOutlined />} />
              <Statistic title="Resolved" value={mantisResolved} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
              <Statistic title="Closed" value={mantisClosed} prefix={<PlayCircleOutlined />} />
            </Space>
            {stats?.mantis?.last_updated && (
              <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                Last sync: {new Date(stats.mantis.last_updated).toLocaleString()}
              </Text>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="Platform Distribution">
            {stats?.vms?.vms?.by_platform && (
              <Space direction="vertical" size={6}>
                <Text>FortiGate: {stats.vms.vms.by_platform.FortiGate}</Text>
                <Text>FortiAuthenticator: {stats.vms.vms.by_platform.FortiAuthenticator}</Text>
              </Space>
            )}
            <Divider />
            <Space size={12}>
              <Tag color="green">Running: {runningVms}</Tag>
              <Tag color="orange">Testing: {testingVms}</Tag>
              <Tag>Stopped: {stoppedVms}</Tag>
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Device Distribution">
            {stats?.devices?.by_platform && (
              <Space direction="vertical" size={6}>
                <Text>iOS: {stats.devices.by_platform.iOS}</Text>
                <Text>Android: {stats.devices.by_platform.Android}</Text>
              </Space>
            )}
            <Divider />
            <Space size={12}>
              <Tag color="green">Available: {availableDevices}</Tag>
              <Tag color="orange">Busy: {busyDevices}</Tag>
              <Tag color="red">Offline: {stats?.devices?.by_status?.offline || 0}</Tag>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
