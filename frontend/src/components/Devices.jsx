import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Row, Statistic, Table, Tag, message } from 'antd';
import axios from 'axios';
import { API_URL } from '../constants';

const Devices = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState({ total: 0, available: 0, unavailable: 0 });

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      // Fetch devices from the new stream endpoint
      const response = await axios.get(`${API_URL}/api/devices/stream/list`);

      const { devices: devicesData, summary: summaryData } = response.data;

      setSummary(summaryData);
      setDevices(devicesData);
      setLoading(false);
    } catch (error) {
      message.error('Failed to fetch devices');
      setLoading(false);
    }
  };

  const refreshDevices = async () => {
    try {
      setLoading(true);
      await fetchDevices();
      message.success('Devices refreshed');
    } catch (error) {
      message.error('Failed to refresh devices');
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform) => {
        const label = platform || 'Unknown';
        const color = label === 'iOS' ? 'blue' : label === 'Android' ? 'green' : undefined;
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: 'OS Version',
      dataIndex: 'os_version',
      key: 'os_version',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'available' ? 'green' : status === 'not available' ? 'red' : undefined;
        return <Tag color={color}>{status ? status.toUpperCase() : 'UNKNOWN'}</Tag>;
      },
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (value) => value || 'Unknown',
    },
    {
      title: 'Host',
      dataIndex: 'host',
      key: 'host',
      render: (value) => value || 'N/A',
    },
    {
      title: 'Port',
      dataIndex: 'port',
      key: 'port',
      render: (value) => value || 'N/A',
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic title="Total Nodes" value={summary.total} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="Available Nodes" value={summary.available} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="Unavailable Nodes" value={summary.unavailable} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
      </Row>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h1>Device Nodes</h1>
        <Button type="primary" onClick={refreshDevices}>
          Refresh Nodes
        </Button>
      </div>
      <Table dataSource={devices} columns={columns} rowKey="id" loading={loading} />
    </div>
  );
};

export default Devices;
