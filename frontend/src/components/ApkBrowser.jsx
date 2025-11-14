import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Upload,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography
} from 'antd';
import {
  UploadOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EditOutlined,
  AppleOutlined,
  AndroidOutlined,
  FileOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://10.160.24.60:8000';

const ApkBrowser = () => {
  const [apks, setApks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [selectedApk, setSelectedApk] = useState(null);
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [filterPlatform, setFilterPlatform] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [uploadForm] = Form.useForm();
  const [editForm] = Form.useForm();

  useEffect(() => {
    fetchApks();
    fetchStats();
  }, [filterPlatform, searchText]);

  const fetchApks = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterPlatform) params.platform = filterPlatform;
      if (searchText) params.search = searchText;

      const response = await axios.get(`${API_URL}/api/apks/`, { params });
      setApks(response.data.apk_files || []);
    } catch (error) {
      message.error('Failed to fetch APK files');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/apks/stats/summary`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch APK stats:', error);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('Please select an APK/IPA file');
      return;
    }

    try {
      const values = await uploadForm.validateFields();
      const formData = new FormData();
      formData.append('file', fileList[0].originFileObj || fileList[0]);

      if (values.display_name) formData.append('display_name', values.display_name);
      if (values.description) formData.append('description', values.description);
      if (values.tags) formData.append('tags', values.tags);

      setUploading(true);
      await axios.post(`${API_URL}/api/apks/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      message.success('APK uploaded and parsed successfully');
      setUploadModalVisible(false);
      setFileList([]);
      uploadForm.resetFields();
      fetchApks();
      fetchStats();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Failed to upload APK');
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields();
      await axios.put(`${API_URL}/api/apks/${selectedApk.id}`, values);

      message.success('APK updated successfully');
      setEditModalVisible(false);
      editForm.resetFields();
      setSelectedApk(null);
      fetchApks();
    } catch (error) {
      message.error('Failed to update APK');
    }
  };

  const handleDelete = async (apkId) => {
    try {
      await axios.delete(`${API_URL}/api/apks/${apkId}`);
      message.success('APK deleted successfully');
      fetchApks();
      fetchStats();
    } catch (error) {
      message.error('Failed to delete APK');
    }
  };

  const openEditModal = (apk) => {
    setSelectedApk(apk);
    editForm.setFieldsValue({
      display_name: apk.display_name,
      description: apk.description,
      tags: apk.tags,
      is_active: apk.is_active
    });
    setEditModalVisible(true);
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return dateString ? new Date(dateString).toLocaleString() : 'N/A';
  };

  const columns = [
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      width: 100,
      render: (platform) => {
        const isAndroid = platform === 'android';
        return (
          <Tag icon={isAndroid ? <AndroidOutlined /> : <AppleOutlined />} color={isAndroid ? 'green' : 'blue'}>
            {platform?.toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text) => <Typography.Text strong>{text}</Typography.Text>
    },
    {
      title: 'Package/Bundle',
      key: 'package',
      render: (_, record) => (
        <Typography.Text code>
          {record.package_name || record.bundle_id || 'N/A'}
        </Typography.Text>
      )
    },
    {
      title: 'Version',
      key: 'version',
      render: (_, record) => (
        <div>
          <div>{record.version_name || 'N/A'}</div>
          {record.version_code && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              ({record.version_code})
            </Typography.Text>
          )}
        </div>
      )
    },
    {
      title: 'Size',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size) => formatFileSize(size)
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags) => (
        <>
          {tags?.map(tag => <Tag key={tag}>{tag}</Tag>)}
        </>
      )
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      )
    },
    {
      title: 'Upload Date',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => formatDate(date)
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEditModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete APK"
            description="Are you sure you want to delete this APK file?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const uploadProps = {
    fileList,
    beforeUpload: (file) => {
      const isAPKorIPA = file.name.endsWith('.apk') || file.name.endsWith('.ipa');
      if (!isAPKorIPA) {
        message.error('You can only upload APK or IPA files!');
        return Upload.LIST_IGNORE;
      }
      setFileList([file]);
      return false;
    },
    onRemove: () => {
      setFileList([]);
    },
    maxCount: 1
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>APK/IPA File Manager</h1>
        <Space>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            Upload APK/IPA
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              fetchApks();
              fetchStats();
            }}
          >
            Refresh
          </Button>
        </Space>
      </div>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total APKs"
                value={stats.total_count}
                prefix={<AppstoreOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Android APKs"
                value={stats.android_count}
                prefix={<AndroidOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="iOS IPAs"
                value={stats.ios_count}
                prefix={<AppleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Storage"
                value={stats.total_size_mb}
                suffix="MB"
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="Search by name or package..."
            style={{ width: 300 }}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={() => fetchApks()}
            allowClear
          />
          <Select
            style={{ width: 150 }}
            placeholder="Filter Platform"
            allowClear
            onChange={(value) => setFilterPlatform(value)}
          >
            <Select.Option value="android">Android</Select.Option>
            <Select.Option value="ios">iOS</Select.Option>
          </Select>
        </Space>

        <Table
          dataSource={apks}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Upload Modal */}
      <Modal
        title="Upload APK/IPA File"
        open={uploadModalVisible}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
          uploadForm.resetFields();
        }}
        okText="Upload"
        confirmLoading={uploading}
        width={600}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item
            label="APK/IPA File"
            required
            tooltip="Only .apk and .ipa files are supported"
          >
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>Select File</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            label="Display Name"
            name="display_name"
            tooltip="A user-friendly name for the app"
          >
            <Input placeholder="e.g., FortiClient Mobile v1.2.3" />
          </Form.Item>

          <Form.Item
            label="Description"
            name="description"
          >
            <Input.TextArea
              rows={3}
              placeholder="Optional description"
            />
          </Form.Item>

          <Form.Item
            label="Tags"
            name="tags"
            tooltip="Comma-separated tags for organization"
          >
            <Input placeholder="e.g., production, release, fac" />
          </Form.Item>
        </Form>

        {fileList.length > 0 && (
          <Typography.Text type="secondary">
            File metadata will be automatically extracted after upload
          </Typography.Text>
        )}
      </Modal>

      {/* Edit Modal */}
      <Modal
        title={`Edit APK: ${selectedApk?.display_name}`}
        open={editModalVisible}
        onOk={handleEdit}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          setSelectedApk(null);
        }}
        okText="Save"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            label="Display Name"
            name="display_name"
            rules={[{ required: true, message: 'Please enter display name' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            label="Description"
            name="description"
          >
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item
            label="Tags"
            name="tags"
          >
            <Select mode="tags" placeholder="Enter tags" />
          </Form.Item>

          <Form.Item
            label="Status"
            name="is_active"
            valuePropName="checked"
          >
            <Select>
              <Select.Option value={true}>Active</Select.Option>
              <Select.Option value={false}>Inactive</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApkBrowser;
