import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Form,
  Image,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tooltip,
  Upload,
  message
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  QrcodeOutlined,
  ReloadOutlined,
  UploadOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const Files = () => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [qrModalVisible, setQrModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [qrData, setQrData] = useState(null);
  const [editingFileName, setEditingFileName] = useState('');
  const [fileList, setFileList] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [form] = Form.useForm();

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/`);
      setFiles(response.data);
    } catch (error) {
      message.error('Failed to fetch files');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('Please select at least one file');
      return;
    }

    const formData = new FormData();
    fileList.forEach(file => {
      formData.append('files', file.originFileObj || file);
    });

    setLoading(true);
    try {
      await axios.post(`${API_URL}/api/files/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      message.success('Files uploaded successfully');
      setUploadModalVisible(false);
      setFileList([]);
      fetchFiles();
    } catch (error) {
      message.error('Failed to upload files');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (filename) => {
    window.open(`${API_URL}/uploads/${encodeURIComponent(filename)}`, '_blank');
  };

  const buildFileUrl = (path) => {
    if (!path) return '';
    const base = API_URL?.replace(/\/$/, '') || '';
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${base}${normalizedPath}`;
  };

  const handleGenerateQr = async (path) => {
    try {
      const url = buildFileUrl(path);
      const response = await axios.post(`${API_URL}/api/files/qrcode`, { url });
      setQrData({
        qrDataUrl: response.data.qr,
        downloadUrl: url,
        filename: path,
      });
      setQrModalVisible(true);
    } catch (error) {
      message.error('Failed to generate QR code');
    }
  };

  const handleEditFile = async (filename) => {
    setEditingFileName(filename);
    setEditModalVisible(true);
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/files/${encodeURIComponent(filename)}`);
      form.setFieldsValue({
        newName: filename,
        content: response.data.content,
      });
    } catch (error) {
      message.error('Failed to load file content');
      setEditModalVisible(false);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveFile = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await axios.put(`${API_URL}/api/files/${encodeURIComponent(editingFileName)}`, {
        new_name: values.newName,
        content: values.content,
      });
      message.success('File saved successfully');
      setEditModalVisible(false);
      form.resetFields();
      fetchFiles();
    } catch (error) {
      message.error('Failed to save file');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (filename) => {
    setLoading(true);
    try {
      await axios.delete(`${API_URL}/api/files/${encodeURIComponent(filename)}`);
      message.success('File deleted');
      fetchFiles();
    } catch (error) {
      message.error('Failed to delete file');
    } finally {
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
      title: 'Last Modified',
      dataIndex: 'last_modified',
      key: 'last_modified',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="Download">
            <Button
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.name)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="Generate QR">
            <Button
              icon={<QrcodeOutlined />}
              onClick={() => handleGenerateQr(record.path || record.name)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="View/Edit">
            <Button
              icon={<EditOutlined />}
              onClick={() => handleEditFile(record.name)}
              size="small"
            />
          </Tooltip>
          <Popconfirm
            title="Are you sure you want to delete this file?"
            onConfirm={() => handleDelete(record.name)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                icon={<DeleteOutlined />}
                danger
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const filteredFiles = files.filter((file) =>
    file.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (file.path || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const uploadProps = {
    multiple: true,
    fileList: fileList,
    beforeUpload: (file) => {
      setFileList([...fileList, file]);
      return false;
    },
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>File Browser</h1>
        <Space>
          <Input
            allowClear
            placeholder="Filter files"
            style={{ minWidth: 280 }}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalVisible(true)}
          >
            Upload Files
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchFiles}
          >
            Refresh
          </Button>
        </Space>
      </div>

      <Card>
        <Table
          dataSource={filteredFiles}
          columns={columns}
          rowKey="name"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title="Upload Files"
        open={uploadModalVisible}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
        }}
        okText="Upload"
        confirmLoading={loading}
      >
        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">Click or drag files to this area to upload</p>
          <p className="ant-upload-hint">Support for single or bulk upload</p>
        </Upload.Dragger>
      </Modal>

      <Modal
        title="QR Code for Download"
        open={qrModalVisible}
        onCancel={() => {
          setQrModalVisible(false);
          setQrData(null);
        }}
        footer={[
          <Button key="close" onClick={() => setQrModalVisible(false)}>
            Close
          </Button>
        ]}
      >
        {qrData && (
          <div style={{ textAlign: 'center' }}>
            <p><strong>File:</strong> {qrData.filename}</p>
            <Image
              src={qrData.qrDataUrl}
              alt="QR Code"
              style={{ maxWidth: '100%' }}
              preview={false}
            />
            <p style={{ marginTop: 16, wordBreak: 'break-all' }}>
              <strong>Download URL:</strong><br />
              <a href={qrData.downloadUrl} target="_blank" rel="noopener noreferrer">
                {qrData.downloadUrl}
              </a>
            </p>
          </div>
        )}
      </Modal>

      <Modal
        title={`Edit File: ${editingFileName}`}
        open={editModalVisible}
        onOk={handleSaveFile}
        onCancel={() => {
          setEditModalVisible(false);
          form.resetFields();
        }}
        okText="Save"
        confirmLoading={loading}
        width={800}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="File Name"
            name="newName"
            rules={[{ required: true, message: 'Please enter a file name' }]}
          >
            <Input placeholder="Enter new file name" />
          </Form.Item>
          <Form.Item
            label="Content"
            name="content"
            rules={[{ required: true, message: 'Content cannot be empty' }]}
          >
            <Input.TextArea
              rows={15}
              placeholder="File content"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Files;
