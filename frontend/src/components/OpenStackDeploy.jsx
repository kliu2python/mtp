import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Table,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Popconfirm,
  Tabs,
  Divider,
  Alert,
  Spin,
  Checkbox,
  Steps,
  Typography
} from 'antd';
import {
  CloudServerOutlined,
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  ApiOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Option } = Select;
const { TabPane } = Tabs;
const { Step } = Steps;
const { Title, Text } = Typography;

const API_URL = import.meta.env.VITE_API_URL || 'http://10.160.24.60:8000';

const OpenStackDeploy = () => {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(false);
  const [credentialModalVisible, setCredentialModalVisible] = useState(false);
  const [deployModalVisible, setDeployModalVisible] = useState(false);
  const [credentialForm] = Form.useForm();
  const [deployForm] = Form.useForm();

  // Deployment wizard state
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedCredential, setSelectedCredential] = useState(null);
  const [flavors, setFlavors] = useState([]);
  const [images, setImages] = useState([]);
  const [networks, setNetworks] = useState([]);
  const [loadingResources, setLoadingResources] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/openstack/credentials`);
      setCredentials(response.data);
    } catch (error) {
      message.error('Failed to fetch credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCredential = async (values) => {
    try {
      await axios.post(`${API_URL}/api/openstack/credentials`, values);
      message.success('Credential created successfully');
      setCredentialModalVisible(false);
      credentialForm.resetFields();
      fetchCredentials();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to create credential');
    }
  };

  const handleTestConnection = async (credentialId) => {
    setTestingConnection(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/openstack/credentials/${credentialId}/test`
      );

      if (response.data.success) {
        message.success('Connection successful!');
        Modal.success({
          title: 'Connection Successful',
          content: (
            <div>
              <p><strong>Project:</strong> {response.data.project_name}</p>
              <p><strong>Region:</strong> {response.data.region || 'Default'}</p>
              <p><strong>Auth URL:</strong> {response.data.auth_url}</p>
            </div>
          )
        });
      } else {
        message.error(`Connection failed: ${response.data.error}`);
      }
    } catch (error) {
      message.error('Failed to test connection');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleDeleteCredential = async (credentialId) => {
    try {
      await axios.delete(`${API_URL}/api/openstack/credentials/${credentialId}`);
      message.success('Credential deleted successfully');
      fetchCredentials();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to delete credential');
    }
  };

  const handleOpenDeployWizard = () => {
    setDeployModalVisible(true);
    setCurrentStep(0);
    deployForm.resetFields();
  };

  const loadOpenStackResources = async (credentialId) => {
    setLoadingResources(true);
    try {
      const [flavorsRes, imagesRes, networksRes] = await Promise.all([
        axios.get(`${API_URL}/api/openstack/credentials/${credentialId}/flavors`),
        axios.get(`${API_URL}/api/openstack/credentials/${credentialId}/images`),
        axios.get(`${API_URL}/api/openstack/credentials/${credentialId}/networks`)
      ]);

      setFlavors(flavorsRes.data.flavors);
      setImages(imagesRes.data.images);
      setNetworks(networksRes.data.networks);
    } catch (error) {
      message.error('Failed to load OpenStack resources');
    } finally {
      setLoadingResources(false);
    }
  };

  const handleCredentialSelect = (credentialId) => {
    setSelectedCredential(credentialId);
    deployForm.setFieldsValue({ credential_id: credentialId });
    loadOpenStackResources(credentialId);
  };

  const handlePlatformSelect = (platform) => {
    deployForm.setFieldsValue({ platform });
    // Filter images by platform
    loadOpenStackResources(selectedCredential);
  };

  const handleDeployVM = async (values) => {
    try {
      const response = await axios.post(`${API_URL}/api/openstack/deploy`, values);
      message.success(`VM ${values.name} deployed successfully!`);
      setDeployModalVisible(false);
      deployForm.resetFields();
      setCurrentStep(0);

      // Show deployment details
      Modal.success({
        title: 'VM Deployed Successfully',
        content: (
          <div>
            <p><strong>Name:</strong> {response.data.name}</p>
            <p><strong>Platform:</strong> {response.data.platform}</p>
            <p><strong>IP Address:</strong> {response.data.ip_address || 'Provisioning...'}</p>
            <p><strong>Status:</strong> {response.data.status}</p>
          </div>
        )
      });
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to deploy VM');
    }
  };

  const nextStep = () => {
    deployForm.validateFields().then(() => {
      setCurrentStep(currentStep + 1);
    }).catch(() => {
      message.warning('Please fill in all required fields');
    });
  };

  const prevStep = () => {
    setCurrentStep(currentStep - 1);
  };

  const credentialColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: 'Auth URL',
      dataIndex: 'auth_url',
      key: 'auth_url',
      ellipsis: true
    },
    {
      title: 'Project',
      dataIndex: 'project_name',
      key: 'project_name'
    },
    {
      title: 'Region',
      dataIndex: 'region_name',
      key: 'region_name',
      render: (region) => region || 'Default'
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (is_active) => (
        <Tag color={is_active ? 'green' : 'red'}>
          {is_active ? 'Active' : 'Inactive'}
        </Tag>
      )
    },
    {
      title: 'Last Verified',
      dataIndex: 'last_verified',
      key: 'last_verified',
      render: (date) => date ? new Date(date).toLocaleString() : 'Never'
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<ApiOutlined />}
            onClick={() => handleTestConnection(record.id)}
            loading={testingConnection}
          >
            Test
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this credential?"
            onConfirm={() => handleDeleteCredential(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card>
            <Space style={{ marginBottom: 16 }}>
              <Title level={2}>
                <CloudServerOutlined /> OpenStack VM Deployment
              </Title>
            </Space>
            <Alert
              message="Deploy FortiGate and FortiAuthenticator VMs in OpenStack"
              description="Manage OpenStack credentials and automatically deploy VMs with pre-configured images."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="credentials">
        <TabPane tab="Credentials" key="credentials">
          <Card
            title="OpenStack Credentials"
            extra={
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCredentialModalVisible(true)}
                >
                  Add Credential
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={fetchCredentials}
                  loading={loading}
                >
                  Refresh
                </Button>
              </Space>
            }
          >
            <Table
              columns={credentialColumns}
              dataSource={credentials}
              rowKey="id"
              loading={loading}
            />
          </Card>
        </TabPane>

        <TabPane tab="Deploy VM" key="deploy">
          <Card
            title="Deploy New VM"
            extra={
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleOpenDeployWizard}
                disabled={credentials.length === 0}
              >
                Start Deployment
              </Button>
            }
          >
            {credentials.length === 0 ? (
              <Alert
                message="No Credentials Available"
                description="Please add an OpenStack credential first before deploying VMs."
                type="warning"
                showIcon
              />
            ) : (
              <Alert
                message="Ready to Deploy"
                description="Click 'Start Deployment' to begin the VM deployment wizard."
                type="success"
                showIcon
              />
            )}
          </Card>
        </TabPane>
      </Tabs>

      {/* Add Credential Modal */}
      <Modal
        title="Add OpenStack Credential"
        open={credentialModalVisible}
        onCancel={() => {
          setCredentialModalVisible(false);
          credentialForm.resetFields();
        }}
        onOk={() => credentialForm.submit()}
        width={600}
      >
        <Form
          form={credentialForm}
          layout="vertical"
          onFinish={handleCreateCredential}
        >
          <Form.Item
            name="name"
            label="Credential Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="My OpenStack" />
          </Form.Item>

          <Form.Item
            name="auth_url"
            label="Auth URL"
            rules={[{ required: true, message: 'Please enter auth URL' }]}
          >
            <Input placeholder="https://openstack.example.com:5000/v3" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="username"
                label="Username"
                rules={[{ required: true, message: 'Please enter username' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="password"
                label="Password"
                rules={[{ required: true, message: 'Please enter password' }]}
              >
                <Input.Password />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="project_name"
            label="Project Name"
            rules={[{ required: true, message: 'Please enter project name' }]}
          >
            <Input />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="project_domain_name"
                label="Project Domain"
                initialValue="Default"
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="user_domain_name"
                label="User Domain"
                initialValue="Default"
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="region_name" label="Region (Optional)">
            <Input placeholder="RegionOne" />
          </Form.Item>

          <Form.Item name="description" label="Description (Optional)">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="verify_ssl" valuePropName="checked" initialValue={true}>
            <Checkbox>Verify SSL Certificate</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      {/* Deploy VM Wizard Modal */}
      <Modal
        title="Deploy VM - Wizard"
        open={deployModalVisible}
        onCancel={() => {
          setDeployModalVisible(false);
          setCurrentStep(0);
          deployForm.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="Select Credential" />
          <Step title="Choose Platform" />
          <Step title="Configure VM" />
          <Step title="Review & Deploy" />
        </Steps>

        <Form
          form={deployForm}
          layout="vertical"
          onFinish={handleDeployVM}
        >
          {/* Step 0: Select Credential */}
          {currentStep === 0 && (
            <div>
              <Form.Item
                name="credential_id"
                label="Select OpenStack Credential"
                rules={[{ required: true, message: 'Please select a credential' }]}
              >
                <Select
                  placeholder="Select credential"
                  onChange={handleCredentialSelect}
                >
                  {credentials.map(cred => (
                    <Option key={cred.id} value={cred.id}>
                      {cred.name} ({cred.project_name})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
              {selectedCredential && loadingResources && (
                <Spin tip="Loading OpenStack resources...">
                  <div style={{ padding: 50 }} />
                </Spin>
              )}
            </div>
          )}

          {/* Step 1: Choose Platform */}
          {currentStep === 1 && (
            <div>
              <Form.Item
                name="platform"
                label="Select Platform"
                rules={[{ required: true, message: 'Please select a platform' }]}
              >
                <Select
                  placeholder="Select platform"
                  onChange={handlePlatformSelect}
                >
                  <Option value="FortiGate">FortiGate</Option>
                  <Option value="FortiAuthenticator">FortiAuthenticator</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="version"
                label="Version"
                rules={[{ required: true, message: 'Please enter version' }]}
              >
                <Input placeholder="7.0.0" />
              </Form.Item>
            </div>
          )}

          {/* Step 2: Configure VM */}
          {currentStep === 2 && (
            <div>
              <Form.Item
                name="name"
                label="VM Name"
                rules={[{ required: true, message: 'Please enter VM name' }]}
              >
                <Input placeholder="my-fortigate-vm" />
              </Form.Item>

              <Form.Item
                name="image_id"
                label="Select Image"
                rules={[{ required: true, message: 'Please select an image' }]}
              >
                <Select placeholder="Select image" showSearch>
                  {images.map(image => (
                    <Option key={image.id} value={image.id}>
                      {image.name} ({image.status})
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="flavor"
                label="Select Flavor"
                rules={[{ required: true, message: 'Please select a flavor' }]}
              >
                <Select placeholder="Select flavor">
                  {flavors.map(flavor => (
                    <Option key={flavor.id} value={flavor.id}>
                      {flavor.name} ({flavor.vcpus} vCPUs, {flavor.ram} MB RAM)
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="network_id" label="Network (Optional)">
                <Select placeholder="Select network" allowClear>
                  {networks.map(network => (
                    <Option key={network.id} value={network.id}>
                      {network.name} ({network.status})
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="ssh_username"
                label="SSH Username"
                initialValue="admin"
              >
                <Input />
              </Form.Item>

              <Form.Item name="ssh_password" label="SSH Password (Optional)">
                <Input.Password />
              </Form.Item>

              <Form.Item
                name="assign_floating_ip"
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Assign Floating IP</Checkbox>
              </Form.Item>
            </div>
          )}

          {/* Step 3: Review & Deploy */}
          {currentStep === 3 && (
            <div>
              <Alert
                message="Review Configuration"
                description="Please review the configuration before deploying."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Divider />
              <p><strong>Credential:</strong> {credentials.find(c => c.id === selectedCredential)?.name}</p>
              <p><strong>Platform:</strong> {deployForm.getFieldValue('platform')}</p>
              <p><strong>Version:</strong> {deployForm.getFieldValue('version')}</p>
              <p><strong>VM Name:</strong> {deployForm.getFieldValue('name')}</p>
              <p><strong>Flavor:</strong> {flavors.find(f => f.id === deployForm.getFieldValue('flavor'))?.name}</p>
              <p><strong>Assign Floating IP:</strong> {deployForm.getFieldValue('assign_floating_ip') ? 'Yes' : 'No'}</p>
            </div>
          )}

          {/* Navigation Buttons */}
          <Divider />
          <Space style={{ float: 'right' }}>
            {currentStep > 0 && (
              <Button onClick={prevStep}>
                Previous
              </Button>
            )}
            {currentStep < 3 && (
              <Button type="primary" onClick={nextStep}>
                Next
              </Button>
            )}
            {currentStep === 3 && (
              <Button type="primary" htmlType="submit">
                Deploy
              </Button>
            )}
          </Space>
        </Form>
      </Modal>
    </div>
  );
};

export default OpenStackDeploy;
