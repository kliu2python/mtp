import React, { useState, useEffect } from 'react';
import {
  Modal,
  Table,
  Tag,
  Space,
  Input,
  Select,
  Button,
  message,
  Checkbox,
  Alert,
  Typography
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  AndroidOutlined,
  AppleOutlined
} from '@ant-design/icons';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const DeviceSelector = ({ visible, onCancel, onSelect, selectedDeviceIds = [], multiSelect = true }) => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState(selectedDeviceIds);
  const [filterPlatform, setFilterPlatform] = useState(null);
  const [filterOsVersion, setFilterOsVersion] = useState('');
  const [filterStatus, setFilterStatus] = useState('available');
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    if (visible) {
      fetchDevices();
      setSelectedIds(selectedDeviceIds);
    }
  }, [visible, selectedDeviceIds, filterPlatform, filterOsVersion, filterStatus, searchText]);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterPlatform) params.platform = filterPlatform;
      if (filterOsVersion) params.os_version = filterOsVersion;
      if (filterStatus) params.status = filterStatus;

      const response = await axios.get(`${API_URL}/api/devices`, { params });
      let deviceList = response.data.devices || [];

      // Apply search filter on client side
      if (searchText) {
        const search = searchText.toLowerCase();
        deviceList = deviceList.filter(d =>
          d.name?.toLowerCase().includes(search) ||
          d.device_id?.toLowerCase().includes(search) ||
          d.platform?.toLowerCase().includes(search)
        );
      }

      setDevices(deviceList);
    } catch (error) {
      message.error('Failed to fetch devices');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = () => {
    if (selectedIds.length === 0) {
      message.warning('Please select at least one device');
      return;
    }

    const selectedDevices = devices.filter(d => selectedIds.includes(d.id));
    onSelect(selectedDevices);
    onCancel();
  };

  const rowSelection = {
    type: multiSelect ? 'checkbox' : 'radio',
    selectedRowKeys: selectedIds,
    onChange: (selectedRowKeys) => {
      setSelectedIds(selectedRowKeys);
    },
    getCheckboxProps: (record) => ({
      disabled: record.status !== 'available'
    })
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Typography.Text strong>{text}</Typography.Text>
    },
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform) => {
        const isAndroid = platform?.toLowerCase().includes('android');
        const isIOS = platform?.toLowerCase().includes('ios');
        return (
          <Tag
            icon={isAndroid ? <AndroidOutlined /> : isIOS ? <AppleOutlined /> : null}
            color={isAndroid ? 'green' : isIOS ? 'blue' : 'default'}
          >
            {platform}
          </Tag>
        );
      }
    },
    {
      title: 'OS Version',
      dataIndex: 'os_version',
      key: 'os_version'
    },
    {
      title: 'Device Type',
      dataIndex: 'device_type',
      key: 'device_type',
      render: (type) => {
        if (!type) return 'N/A';
        const isPhysical = type.includes('physical');
        return (
          <Tag color={isPhysical ? 'blue' : 'default'}>
            {type.replace('_', ' ').toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const isAvailable = status === 'available';
        return (
          <Tag
            icon={isAvailable ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            color={isAvailable ? 'success' : status === 'busy' ? 'processing' : 'default'}
          >
            {status?.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Battery',
      dataIndex: 'battery_level',
      key: 'battery_level',
      render: (level) => level ? `${level}%` : 'N/A'
    },
    {
      title: 'Location',
      dataIndex: 'location',
      key: 'location',
      render: (location) => location || 'N/A'
    }
  ];

  return (
    <Modal
      title="Select Device(s)"
      open={visible}
      onCancel={onCancel}
      onOk={handleSelect}
      width={1000}
      okText={`Select (${selectedIds.length})`}
      okButtonProps={{ disabled: selectedIds.length === 0 }}
    >
      <Alert
        message={multiSelect ? 'Multi-Device Selection' : 'Single Device Selection'}
        description={
          multiSelect
            ? 'You can select multiple devices for parallel testing'
            : 'Select one device for testing'
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Space style={{ marginBottom: 16, width: '100%' }} wrap>
        <Input.Search
          placeholder="Search devices..."
          style={{ width: 250 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
        />

        <Select
          style={{ width: 150 }}
          placeholder="Platform"
          allowClear
          value={filterPlatform}
          onChange={setFilterPlatform}
        >
          <Select.Option value="Android">Android</Select.Option>
          <Select.Option value="iOS">iOS</Select.Option>
        </Select>

        <Input
          style={{ width: 150 }}
          placeholder="OS Version"
          value={filterOsVersion}
          onChange={(e) => setFilterOsVersion(e.target.value)}
          allowClear
        />

        <Select
          style={{ width: 150 }}
          placeholder="Status"
          value={filterStatus}
          onChange={setFilterStatus}
          allowClear
        >
          <Select.Option value="available">Available</Select.Option>
          <Select.Option value="busy">Busy</Select.Option>
          <Select.Option value="offline">Offline</Select.Option>
        </Select>

        <Button
          icon={<ReloadOutlined />}
          onClick={fetchDevices}
          loading={loading}
        >
          Refresh
        </Button>
      </Space>

      <Table
        rowSelection={rowSelection}
        dataSource={devices}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 8, showSizeChanger: false }}
        scroll={{ y: 400 }}
        size="small"
      />

      {selectedIds.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <Typography.Text strong>
            Selected: {selectedIds.length} device{selectedIds.length > 1 ? 's' : ''}
          </Typography.Text>
        </div>
      )}
    </Modal>
  );
};

export default DeviceSelector;
