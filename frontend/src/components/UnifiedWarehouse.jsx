import React, { useState, useEffect } from 'react';
import {
  Button,
  Card,
  Input,
  Modal,
  Select,
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

const { Option } = Select;

// Unified Warehouse Functions
const fetchWarehouseCounts = async (setCounts) => {
  try {
    const response = await axios.get(`${API_URL}/api/warehouse/count`);
    setCounts(response.data);
  } catch (error) {
    // Silent fail, will show 0 counts
  }
};

const handleCopyRandomCode = async (selectedType, setLoading, setCounts) => {
  setLoading(true);
  try {
    const response = await axios.post(`${API_URL}/api/warehouse/random`, null, {
      params: { code_type: selectedType === 'All' ? null : selectedType }
    });

    if (response.data.code) {
      let successMessage = `${response.data.code_type} code copied to clipboard`;
      if (response.data.size) {
        successMessage += ` (Size: ${response.data.size})`;
      }
      await navigator.clipboard.writeText(response.data.code);
      message.success(successMessage);
      fetchWarehouseCounts(setCounts);
    } else {
      message.warning('No available codes');
    }
  } catch (error) {
    message.error('Failed to retrieve code');
  } finally {
    setLoading(false);
  }
};

const handleRecycleCode = async (recycleCode, setRecycleCode, setLoading, setCounts) => {
  if (!recycleCode.trim()) {
    message.warning('Please enter a code to recycle');
    return;
  }

  setLoading(true);
  try {
    await axios.post(`${API_URL}/api/warehouse/recycle`, { code: recycleCode.trim() });
    message.success('Code recycled successfully');
    setRecycleCode('');
    fetchWarehouseCounts(setCounts);
  } catch (error) {
    console.error('Recycle error:', error);
    message.error('Failed to recycle code: ' + (error.response?.data?.detail || error.message));
  } finally {
    setLoading(false);
  }
};

const handleUploadCodes = async (fileList, setUploadModalVisible, setFileList, setLoading, setCounts) => {
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
    const response = await axios.post(`${API_URL}/api/warehouse/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    message.success(`Successfully uploaded ${fileList.length} files`);
    setUploadModalVisible(false);
    setFileList([]);
    // Refresh count after upload
    fetchWarehouseCounts(setCounts);
  } catch (error) {
    console.error('Upload error:', error);
    message.error('Failed to upload files: ' + (error.response?.data?.detail || error.message));
  } finally {
    setLoading(false);
  }
};

const UnifiedWarehouse = () => {
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [fileList, setFileList] = useState([]);

  // Warehouse states
  const [counts, setCounts] = useState({
    fortigate: 0,
    fortiauthenticator: 0,
    fortitoken: 0,
    fortidentitycloud: 0,
    total: 0
  });
  const [selectedType, setSelectedType] = useState('All');
  const [recycleCode, setRecycleCode] = useState('');

  // Load counts on component mount
  useEffect(() => {
    fetchWarehouseCounts(setCounts);
  }, []);

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

  const handleUpload = async () => {
    await handleUploadCodes(fileList, setUploadModalVisible, setFileList, setLoading, setCounts);
  };

  return (
    <div>
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>

          <div style={{ marginBottom: '25px' }}>
            <h3 style={{ marginTop: 0, marginBottom: '15px', textAlign: 'center' }}>Select license Type</h3>
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '15px',
              flexWrap: 'wrap'
            }}>
              <div
                onClick={() => setSelectedType('All')}
                style={{
                  backgroundColor: selectedType === 'All' ? '#1890ff' : '#f0f5ff',
                  padding: '15px 20px',
                  borderRadius: '6px',
                  minWidth: '100px',
                  boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                  border: selectedType === 'All' ? '2px solid #1890ff' : '1px solid #d9e7ff',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  transform: selectedType === 'All' ? 'scale(1.05)' : 'scale(1)'
                }}
              >
                <div style={{ fontSize: '14px', color: selectedType === 'All' ? '#fff' : '#666' }}>Total</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: selectedType === 'All' ? '#fff' : '#1890ff' }}>{counts.total}</div>
              </div>
              <div
                onClick={() => setSelectedType('FortiGate')}
                style={{
                  backgroundColor: selectedType === 'FortiGate' ? '#52c41a' : '#fff',
                  padding: '15px 20px',
                  borderRadius: '6px',
                  minWidth: '100px',
                  boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                  border: selectedType === 'FortiGate' ? '2px solid #52c41a' : '1px solid #e8e8e8',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  transform: selectedType === 'FortiGate' ? 'scale(1.05)' : 'scale(1)'
                }}
              >
                <div style={{ fontSize: '14px', color: selectedType === 'FortiGate' ? '#fff' : '#666' }}>FortiGate</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: selectedType === 'FortiGate' ? '#fff' : '#52c41a' }}>{counts.fortigate}</div>
              </div>
              <div
                onClick={() => setSelectedType('FortiAuthenticator')}
                style={{
                  backgroundColor: selectedType === 'FortiAuthenticator' ? '#fa8c16' : '#fff',
                  padding: '15px 20px',
                  borderRadius: '6px',
                  minWidth: '100px',
                  boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                  border: selectedType === 'FortiAuthenticator' ? '2px solid #fa8c16' : '1px solid #e8e8e8',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  transform: selectedType === 'FortiAuthenticator' ? 'scale(1.05)' : 'scale(1)'
                }}
              >
                <div style={{ fontSize: '14px', color: selectedType === 'FortiAuthenticator' ? '#fff' : '#666' }}>FortiAuth</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: selectedType === 'FortiAuthenticator' ? '#fff' : '#fa8c16' }}>{counts.fortiauthenticator}</div>
              </div>
              <div
                onClick={() => setSelectedType('FortiToken')}
                style={{
                  backgroundColor: selectedType === 'FortiToken' ? '#722ed1' : '#fff',
                  padding: '15px 20px',
                  borderRadius: '6px',
                  minWidth: '100px',
                  boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                  border: selectedType === 'FortiToken' ? '2px solid #722ed1' : '1px solid #e8e8e8',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  transform: selectedType === 'FortiToken' ? 'scale(1.05)' : 'scale(1)'
                }}
              >
                <div style={{ fontSize: '14px', color: selectedType === 'FortiToken' ? '#fff' : '#666' }}>FortiToken</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: selectedType === 'FortiToken' ? '#fff' : '#722ed1' }}>{counts.fortitoken}</div>
              </div>
              <div
                onClick={() => setSelectedType('FortiIdentityCloud')}
                style={{
                  backgroundColor: selectedType === 'FortiIdentityCloud' ? '#13c2c2' : '#fff',
                  padding: '15px 20px',
                  borderRadius: '6px',
                  minWidth: '100px',
                  boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                  border: selectedType === 'FortiIdentityCloud' ? '2px solid #13c2c2' : '1px solid #e8e8e8',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  transform: selectedType === 'FortiIdentityCloud' ? 'scale(1.05)' : 'scale(1)'
                }}
              >
                <div style={{ fontSize: '14px', color: selectedType === 'FortiIdentityCloud' ? '#fff' : '#666' }}>FIC</div>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: selectedType === 'FortiIdentityCloud' ? '#fff' : '#13c2c2' }}>{counts.fortidentitycloud}</div>
              </div>
            </div>
          </div>

          <Space size="large" style={{ margin: '20px 0' }}>
            <Button
              type="primary"
              icon={<CopyOutlined />}
              size="large"
              onClick={() => handleCopyRandomCode(selectedType, setLoading, setCounts)}
              loading={loading}
              disabled={
                selectedType === 'All' ? true :
                selectedType === 'FortiGate' ? counts.fortigate === 0 :
                selectedType === 'FortiAuthenticator' ? counts.fortiauthenticator === 0 :
                selectedType === 'FortiToken' ? counts.fortitoken === 0 :
                selectedType === 'FortiIdentityCloud' ? counts.fortidentitycloud === 0 :
                counts.total === 0
              }
              style={{ minWidth: '200px' }}
            >
              Copy Random Code
            </Button>

            <Button
              type="default"
              icon={<UploadOutlined />}
              size="large"
              onClick={() => setUploadModalVisible(true)}
              style={{ minWidth: '200px' }}
            >
              Upload PDFs
            </Button>

            <Button
              onClick={() => fetchWarehouseCounts(setCounts)}
            >
              Refresh
            </Button>
          </Space>

          {/* Recycle Section */}
          <div style={{ marginTop: 40, paddingTop: 30, borderTop: '1px solid #eee' }}>
            <h3>Recycle Code</h3>
            <p style={{ color: '#666' }}>If a copied code was not used, you can recycle it back into the pool.</p>
            <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: '400px', margin: '0 auto' }}>
              <Input
                placeholder="Enter code to recycle"
                value={recycleCode}
                onChange={(e) => setRecycleCode(e.target.value)}
                style={{ width: '100%' }}
              />
              <Button
                type="dashed"
                onClick={() => handleRecycleCode(recycleCode, setRecycleCode, setLoading, setCounts)}
                disabled={!recycleCode.trim()}
                loading={loading}
                style={{ width: '100%' }}
              >
                Recycle Code
              </Button>
            </Space>
          </div>
        </div>
      </Card>

      <Modal
        title="Upload PDF Files"
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
          <p className="ant-upload-hint">
            Only PDF files containing FortiGate, FortiAuthenticator, FortiIdentity Cloud, or FortiToken codes are supported
          </p>
        </Upload.Dragger>
      </Modal>
    </div>
  );
};

export default UnifiedWarehouse;