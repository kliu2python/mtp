import React, { useState } from 'react';
import {
  Button,
  Card,
  Input,
  Modal,
  Select,
  Space,
  Upload,
  Tabs,
  message
} from 'antd';
import {
  CopyOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { TabPane } = Tabs;
const { Option } = Select;

// FortiToken Functions
const fetchAvailableTokensCount = async (setAvailableTokens) => {
  try {
    const response = await axios.get(`${API_URL}/api/warehouse/count`);
    setAvailableTokens(response.data.fortitoken || 0);
  } catch (error) {
    // Silent fail, will show 0 tokens
  }
};

const handleCopyRandomToken = async (setLoading, setAvailableTokens) => {
  setLoading(true);
  try {
    const response = await axios.post(`${API_URL}/api/warehouse/random`, null, {
      params: { code_type: 'FortiToken' }
    });
    if (response.data.code) {
      await navigator.clipboard.writeText(response.data.code);
      message.success('Activation code copied to clipboard');
      fetchAvailableTokensCount(setAvailableTokens);
    } else {
      message.warning('No available activation codes');
    }
  } catch (error) {
    message.error('Failed to retrieve activation code');
  } finally {
    setLoading(false);
  }
};

const handleRecycleToken = async (recycleCode, setRecycleCode, setLoading, setAvailableTokens) => {
  if (!recycleCode.trim()) {
    message.warning('Please enter an activation code to recycle');
    return;
  }

  setLoading(true);
  try {
    await axios.post(`${API_URL}/api/warehouse/recycle`, { code: recycleCode.trim() });
    message.success('Activation code recycled successfully');
    setRecycleCode('');
    fetchAvailableTokensCount(setAvailableTokens);
  } catch (error) {
    console.error('Recycle error:', error);
    message.error('Failed to recycle activation code: ' + (error.response?.data?.detail || error.message));
  } finally {
    setLoading(false);
  }
};

const handleUploadTokens = async (fileList, setUploadModalVisible, setFileList, setLoading, setAvailableTokens) => {
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
    fetchAvailableTokensCount(setAvailableTokens);
  } catch (error) {
    console.error('Upload error:', error);
    message.error('Failed to upload files: ' + (error.response?.data?.detail || error.message));
  } finally {
    setLoading(false);
  }
};

// License Functions
const fetchAvailableLicensesCounts = async (setLicenseCounts) => {
  try {
    // Fetch counts for all types using the new unified warehouse API
    const response = await axios.get(`${API_URL}/api/warehouse/count`);

    setLicenseCounts({
      all: response.data.total || 0,
      fortigate: response.data.fortigate || 0,
      fortiauthenticator: response.data.fortiauthenticator || 0,
      fortidentitycloud: response.data.fortidentitycloud || 0
    });
  } catch (error) {
    // Silent fail, will show 0 licenses
  }
};

const handleCopyRandomLicense = async (selectedLicenseType, setLoading, setLicenseCounts) => {
  setLoading(true);
  try {
    let response;

    // Use the new unified warehouse API for all types
    if (selectedLicenseType === 'All') {
      response = await axios.post(`${API_URL}/api/warehouse/random`);
    } else {
      response = await axios.post(`${API_URL}/api/warehouse/random`, null, {
        params: { code_type: selectedLicenseType }
      });
    }

    if (response.data.code) {
      await navigator.clipboard.writeText(response.data.code);
      message.success('Registration code copied to clipboard');
      fetchAvailableLicensesCounts(setLicenseCounts);
    } else {
      message.warning('No available registration codes');
    }
  } catch (error) {
    message.error('Failed to retrieve registration code');
  } finally {
    setLoading(false);
  }
};

const handleRecycleLicense = async (recycleCode, setRecycleCode, setLoading, setLicenseCounts) => {
  if (!recycleCode.trim()) {
    message.warning('Please enter a registration code to recycle');
    return;
  }

  setLoading(true);
  try {
    await axios.post(`${API_URL}/api/warehouse/recycle`, { code: recycleCode.trim() });
    message.success('Registration code recycled successfully');
    setRecycleCode('');
    fetchAvailableLicensesCounts(setLicenseCounts);
  } catch (error) {
    console.error('Recycle error:', error);
    message.error('Failed to recycle registration code: ' + (error.response?.data?.detail || error.message));
  } finally {
    setLoading(false);
  }
};

const handleUploadLicenses = async (fileList, setUploadModalVisible, setFileList, setLoading, setLicenseCounts) => {
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
    fetchAvailableLicensesCounts(setLicenseCounts);
  } catch (error) {
    console.error('Upload error:', error);
    message.error('Failed to upload files: ' + (error.response?.data?.detail || error.message));
  } finally {
    setLoading(false);
  }
};

const WarehouseTabs = () => {
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [fileList, setFileList] = useState([]);
  const [activeTab, setActiveTab] = useState('fortitokens');

  // FortiToken states
  const [availableTokens, setAvailableTokens] = useState(0);
  const [recycleTokenCode, setRecycleTokenCode] = useState('');

  // License states
  const [licenseCounts, setLicenseCounts] = useState({
    all: 0,
    fortigate: 0,
    fortiauthenticator: 0,
    fortidentitycloud: 0
  });
  const [selectedLicenseType, setSelectedLicenseType] = useState('All');
  const [recycleLicenseCode, setRecycleLicenseCode] = useState('');

  // Load counts on component mount
  React.useEffect(() => {
    fetchAvailableTokensCount(setAvailableTokens);
    fetchAvailableLicensesCounts(setLicenseCounts);
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
    if (activeTab === 'fortitokens') {
      await handleUploadTokens(fileList, setUploadModalVisible, setFileList, setLoading, setAvailableTokens);
    } else {
      await handleUploadLicenses(fileList, setUploadModalVisible, setFileList, setLoading, setAvailableLicenses);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Warehouse</h1>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        tabBarExtraContent={
          <Button
            type="dashed"
            onClick={() => {
              if (activeTab === 'fortitokens') {
                fetchAvailableTokensCount(setAvailableTokens);
              } else {
                fetchAvailableLicensesCounts(setLicenseCounts);
              }
            }}
          >
            Refresh Count
          </Button>
        }
      >
        <TabPane tab="FortiTokens" key="fortitokens">
          <Card>
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <p>Total available Activation Codes: <strong>{availableTokens}</strong></p>

              <Space size="large">
                <Button
                  type="primary"
                  icon={<CopyOutlined />}
                  size="large"
                  onClick={() => handleCopyRandomToken(setLoading, setAvailableTokens)}
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
              </Space>

              {/* Recycle Section */}
              <div style={{ marginTop: 40, paddingTop: 20, borderTop: '1px solid #eee' }}>
                <h3>Recycle Activation Code</h3>
                <p>If a copied activation code was not used, you can recycle it back into the pool.</p>
                <Space direction="vertical" size="middle">
                  <Input
                    placeholder="Enter activation code to recycle (e.g., ABCD-EFGH-IJKL-MNOP-QRST)"
                    value={recycleTokenCode}
                    onChange={(e) => setRecycleTokenCode(e.target.value)}
                    style={{ width: 300 }}
                  />
                  <Button
                    onClick={() => handleRecycleToken(recycleTokenCode, setRecycleTokenCode, setLoading, setAvailableTokens)}
                    disabled={!recycleTokenCode.trim()}
                    loading={loading}
                  >
                    Recycle Code
                  </Button>
                </Space>
              </div>
            </div>
          </Card>
        </TabPane>

        <TabPane tab="Licenses" key="licenses">
          <Card>
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <div style={{ marginBottom: '20px' }}>
                <p>Total available Registration Codes: <strong>{licenseCounts.all}</strong></p>
              </div>

              {/* Box boards for license types */}
              <div style={{ marginBottom: '25px' }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: '15px',
                  flexWrap: 'wrap'
                }}>
                  <div
                    style={{
                      backgroundColor: '#f0f5ff',
                      padding: '15px 20px',
                      borderRadius: '6px',
                      minWidth: '100px',
                      boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                      border: '1px solid #d9e7ff',
                      textAlign: 'center'
                    }}
                  >
                    <div style={{ fontSize: '14px', color: '#666' }}>FortiGate</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#52c41a' }}>{licenseCounts.fortigate}</div>
                  </div>
                  <div
                    style={{
                      backgroundColor: '#f0f5ff',
                      padding: '15px 20px',
                      borderRadius: '6px',
                      minWidth: '100px',
                      boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                      border: '1px solid #d9e7ff',
                      textAlign: 'center'
                    }}
                  >
                    <div style={{ fontSize: '14px', color: '#666' }}>FortiAuth</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#fa8c16' }}>{licenseCounts.fortiauthenticator}</div>
                  </div>
                  <div
                    style={{
                      backgroundColor: '#f0f5ff',
                      padding: '15px 20px',
                      borderRadius: '6px',
                      minWidth: '100px',
                      boxShadow: '0 1px 4px rgba(0, 0, 0, 0.1)',
                      border: '1px solid #d9e7ff',
                      textAlign: 'center'
                    }}
                  >
                    <div style={{ fontSize: '14px', color: '#666' }}>FIC</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#13c2c2' }}>{licenseCounts.fortidentitycloud}</div>
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <Space direction="vertical">
                  <span>Select License Type:</span>
                  <Select
                    value={selectedLicenseType}
                    onChange={setSelectedLicenseType}
                    style={{ width: 200 }}
                  >
                    <Option value="All">All Types</Option>
                    <Option value="FortiGate">FortiGate Only</Option>
                    <Option value="FortiAuthenticator">FortiAuthenticator Only</Option>
                    <Option value="FortiIdentityCloud">FortiIdentity Cloud Only</Option>
                  </Select>
                </Space>
              </div>

              <Space size="large">
                <Button
                  type="primary"
                  icon={<CopyOutlined />}
                  size="large"
                  onClick={() => handleCopyRandomLicense(selectedLicenseType, setLoading, setLicenseCounts)}
                  loading={loading}
                  disabled={selectedLicenseType === 'FortiGate' ? licenseCounts.fortigate === 0 :
                           selectedLicenseType === 'FortiAuthenticator' ? licenseCounts.fortiauthenticator === 0 :
                           selectedLicenseType === 'FortiIdentityCloud' ? licenseCounts.fortidentitycloud === 0 :
                           licenseCounts.all === 0}
                >
                  Copy Random Registration Code
                </Button>

                <Button
                  type="default"
                  icon={<UploadOutlined />}
                  size="large"
                  onClick={() => setUploadModalVisible(true)}
                >
                  Upload PDFs
                </Button>
              </Space>

              {/* Recycle Section */}
              <div style={{ marginTop: 40, paddingTop: 20, borderTop: '1px solid #eee' }}>
                <h3>Recycle Registration Code</h3>
                <p>If a copied registration code was not used, you can recycle it back into the pool.</p>
                <Space direction="vertical" size="middle">
                  <Input
                    placeholder="Enter registration code to recycle (e.g., XXXXX-XXXXX-XXXXX-XXXXX-XXXXXX)"
                    value={recycleLicenseCode}
                    onChange={(e) => setRecycleLicenseCode(e.target.value)}
                    style={{ width: 300 }}
                  />
                  <Button
                    onClick={() => handleRecycleLicense(recycleLicenseCode, setRecycleLicenseCode, setLoading, setLicenseCounts)}
                    disabled={!recycleLicenseCode.trim()}
                    loading={loading}
                  >
                    Recycle Code
                  </Button>
                </Space>
              </div>
            </div>
          </Card>
        </TabPane>
      </Tabs>

      <Modal
        title={activeTab === 'fortitokens' ? "Upload FortiToken PDF Files" : "Upload FortiGate/FortiAuthenticator/FortiIdentity Cloud License PDF Files"}
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
            {activeTab === 'fortitokens'
              ? "Only PDF files containing FortiToken activation codes are supported"
              : "Only PDF files containing FortiGate/FortiAuthenticator registration codes are supported"}
          </p>
        </Upload.Dragger>
      </Modal>
    </div>
  );
};

export default WarehouseTabs;