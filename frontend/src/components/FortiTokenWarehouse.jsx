import React, { useState } from 'react';
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Space,
  Upload,
  message
} from 'antd';
import {
  CopyOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const FortiTokenWarehouse = () => {
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [fileList, setFileList] = useState([]);
  const [availableTokens, setAvailableTokens] = useState(0);
  const [recycleCode, setRecycleCode] = useState('');

  // Load available tokens count on component mount
  React.useEffect(() => {
    fetchAvailableTokensCount();
  }, []);

  const fetchAvailableTokensCount = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/fortitokens/count`);
      setAvailableTokens(response.data.count || 0);
    } catch (error) {
      // Silent fail, will show 0 tokens
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('Please select at least one PDF file');
      return;
    }

    const formData = new FormData();
    fileList.forEach(file => {
      // Use the actual file object
      if (file.originFileObj) {
        formData.append('files', file.originFileObj);
      } else {
        formData.append('files', file);
      }
    });

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/fortitokens/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      message.success(`Successfully uploaded ${fileList.length} files`);
      setUploadModalVisible(false);
      setFileList([]);
      // Refresh count after upload
      fetchAvailableTokensCount();
    } catch (error) {
      console.error('Upload error:', error);
      message.error('Failed to upload files: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCopyRandomCode = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/fortitokens/random`);
      if (response.data.code) {
        await navigator.clipboard.writeText(response.data.code);
        message.success('Activation code copied to clipboard');
        fetchAvailableTokensCount();
      } else {
        message.warning('No available activation codes');
      }
    } catch (error) {
      message.error('Failed to retrieve activation code');
    } finally {
      setLoading(false);
    }
  };

  const handleRecycleCode = async () => {
    if (!recycleCode.trim()) {
      message.warning('Please enter an activation code to recycle');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API_URL}/api/fortitokens/recycle`, { code: recycleCode.trim() });
      message.success('Activation code recycled successfully');
      setRecycleCode('');
      fetchAvailableTokensCount();
    } catch (error) {
      console.error('Recycle error:', error);
      message.error('Failed to recycle activation code: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const uploadProps = {
    multiple: true,
    fileList: fileList,
    accept: '.pdf',
    beforeUpload: (file) => {
      // Only allow PDF files
      if (file.type !== 'application/pdf' && !file.name?.endsWith('.pdf')) {
        message.error('You can only upload PDF files!');
        return false;
      }
      return true; // Return true to allow upload
    },
    onChange: ({ fileList: newFileList }) => {
      // Filter to only include PDF files
      const pdfFiles = newFileList.filter(file =>
        file.status !== 'removed' && (
          file.type === 'application/pdf' ||
          (file.name && file.name.endsWith('.pdf'))
        )
      );
      setFileList(pdfFiles);
    },
    onDrop: (e) => {
      console.log('Dropped files', e.dataTransfer.files);
    },
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Warehouse</h1>
      </div>

      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <p>Total available Activation Code: <strong>{availableTokens}</strong></p>

          <Space size="large">
            <Button
              type="primary"
              icon={<CopyOutlined />}
              size="large"
              onClick={handleCopyRandomCode}
              loading={loading}
              disabled={availableTokens === 0}
            >
              Copy Random Activation Code
            </Button>

            <Button
              type="default"
              icon={<UploadOutlined />}
              size="large"
              onClick={() => setUploadModalVisible(true)}
            >
              Upload PDFs
            </Button>

            <Button
              type="dashed"
              onClick={fetchAvailableTokensCount}
            >
              Refresh Count
            </Button>
          </Space>

          {/* Recycle Section */}
          <div style={{ marginTop: 40, paddingTop: 20, borderTop: '1px solid #eee' }}>
            <h3>Recycle Activation Code</h3>
            <p>If a copied activation code was not used, you can recycle it back into the pool.</p>
            <Space direction="vertical" size="middle">
              <Input
                placeholder="Enter activation code to recycle (e.g., ABCD-EFGH-IJKL-MNOP-QRST)"
                value={recycleCode}
                onChange={(e) => setRecycleCode(e.target.value)}
                style={{ width: 300 }}
              />
              <Button
                onClick={handleRecycleCode}
                disabled={!recycleCode.trim()}
                loading={loading}
              >
                Recycle Code
              </Button>
            </Space>
          </div>
        </div>
      </Card>

      <Modal
        title="Upload FortiToken PDF Files"
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
          <p className="ant-upload-text">Click or drag PDF files to this area to upload</p>
          <p className="ant-upload-hint">Only PDF files containing FortiToken activation codes are supported</p>
        </Upload.Dragger>
      </Modal>
    </div>
  );
};

export default FortiTokenWarehouse;