import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Button, Space, Divider, Tag, message, Form, Input, Select, Switch,
  Table, Popconfirm, Modal
} from 'antd';
import {
  CloudOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  ShopOutlined,
  LinkOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  KeyOutlined,
  UserAddOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { Option } = Select;

const AdminPortal = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [adminToken, setAdminToken] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (!token) {
      message.error('Please login as admin first');
      return;
    }
    setAdminToken(token);
    verifyAdmin(token);
  }, []);

  const verifyAdmin = async (token) => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setIsAdmin(true);
      fetchUsers(token);
    } catch (error) {
      message.error('Admin access denied');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async (token) => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token || adminToken}`
        }
      });
      setUsers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const handleCreateUser = async (values) => {
    try {
      const token = localStorage.getItem('adminToken');
      await axios.post(`${API_URL}/api/admin/users`, values, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      message.success('User created successfully');
      setModalOpen(false);
      form.resetFields();
      fetchUsers();
    } catch (error) {
      console.error('Failed to create user:', error);
      message.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleDeleteUser = async (userId) => {
    try {
      const token = localStorage.getItem('adminToken');
      await axios.delete(`${API_URL}/api/admin/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      message.success('User deleted successfully');
      fetchUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      message.error('Failed to delete user');
    }
  };

  const handleChangePassword = async (values) => {
    try {
      const token = localStorage.getItem('adminToken');
      await axios.post(
        `${API_URL}/api/admin/users/${currentUser.id}/change-password`,
        { new_password: values.new_password },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      message.success('Password changed successfully');
      setPasswordModalOpen(false);
      passwordForm.resetFields();
    } catch (error) {
      console.error('Failed to change password:', error);
      message.error('Failed to change password');
    }
  };

  const userColumns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Full Name',
      dataIndex: 'full_name',
      key: 'full_name',
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>
          {role?.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => (
        <Space>
          <Tag color={record.is_active ? 'green' : 'default'}>
            {record.is_active ? 'Active' : 'Inactive'}
          </Tag>
          {record.is_superuser && (
            <Tag color="purple">Superuser</Tag>
          )}
        </Space>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<KeyOutlined />}
            onClick={() => {
              setCurrentUser(record);
              setPasswordModalOpen(true);
            }}
          >
            Change Password
          </Button>
          <Popconfirm
            title="Delete User"
            description="Are you sure to delete this user?"
            onConfirm={() => handleDeleteUser(record.id)}
            okText="Delete"
            cancelText="Cancel"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const externalServices = [
    {
      title: 'DeviceHub',
      description: '设备中心 - 设备管理和调度',
      icon: <CloudOutlined style={{ fontSize: 36, color: '#1890ff' }} />,
      url: 'https://devicehub.qa.fortinet-us.com',
      tag: 'External',
    },
    {
      title: 'Jenkins',
      description: 'CI/CD 自动化构建和测试',
      icon: <RocketOutlined style={{ fontSize: 36, color: '#d93025' }} />,
      url: 'https://jenkins.qa.fortinet-us.com',
      tag: 'CI/CD',
    },
    {
      title: 'Allure',
      description: '测试报告平台',
      icon: <CheckCircleOutlined style={{ fontSize: 36, color: '#4caf50' }} />,
      url: 'https://allure.qa.fortinet-us.com',
      tag: 'Reports',
    },
    {
      title: 'GitLab',
      description: '代码仓库和版本控制',
      icon: <DatabaseOutlined style={{ fontSize: 36, color: '#fc6c20' }} />,
      url: 'https://gitlab.qa.fortinet-us.com',
      tag: 'Source',
    },
    {
      title: 'Nexus',
      description: '构件仓库管理',
      icon: <ShopOutlined style={{ fontSize: 36, color: '#1ea36d' }} />,
      url: 'https://nexus.qa.fortinet-us.com',
      tag: 'Artifacts',
    },
  ];

  if (loading) {
    return <div style={{ padding: 24, textAlign: 'center' }}>Loading...</div>;
  }

  if (!isAdmin) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <h1>Admin Portal</h1>
        <p>Access Denied - Admin privileges required</p>
        <Button type="primary" onClick={() => window.history.back()}>Go Back</Button>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>
        <SettingOutlined /> Admin Portal
      </h1>

      {/* User Management Section */}
      <Card
        title="User Management"
        extra={
          <Space>
            <Button
              icon={<UserAddOutlined />}
              type="primary"
              onClick={() => setModalOpen(true)}
            >
              Create User
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={() => fetchUsers(adminToken)}
            >
              Refresh
            </Button>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Table
          columns={userColumns}
          dataSource={users}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* External Services Links Section */}
      <h3 style={{ marginBottom: 16 }}>
        <LinkOutlined /> External Services
      </h3>
      <Row gutter={24}>
        {externalServices.map((service, index) => (
          <Col span={8} key={index}>
            <Card
              hoverable
              onClick={() => window.open(service.url, '_blank')}
              style={{
                marginBottom: 16,
                cursor: 'pointer',
                transition: 'transform 0.2s',
              }}
              bodyStyle={{
                display: 'flex',
                alignItems: 'center',
                gap: 16,
              }}
            >
              <div style={{ flexShrink: 0 }}>{service.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontWeight: 'bold', fontSize: 16 }}>
                    {service.title}
                  </span>
                  <Tag color="blue" style={{ fontSize: 10 }}>
                    {service.tag}
                  </Tag>
                </div>
                <div style={{ color: '#666', fontSize: 12 }}>{service.description}</div>
              </div>
              <LinkOutlined style={{ color: '#1890ff', fontSize: 20 }} />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Create User Modal */}
      <Modal
        title="Create User"
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateUser}>
          <Form.Item
            name="username"
            label="Username"
            rules={[
              { required: true, message: 'Please enter username' },
              { min: 3, message: 'Username must be at least 3 characters' }
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Please enter email' },
              { type: 'email', message: 'Please enter a valid email' }
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: 'Please enter password' },
              { min: 6, message: 'Password must be at least 6 characters' }
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="full_name"
            label="Full Name"
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="role"
            label="Role"
            initialValue="admin"
          >
            <Select>
              <Option value="admin">Admin</Option>
              <Option value="user">User</Option>
              <Option value="viewer">Viewer</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="is_superuser"
            label="Superuser"
            valuePropName="checked"
            initialValue={false}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Change Password Modal */}
      <Modal
        title={`Change Password - ${currentUser?.username}`}
        open={passwordModalOpen}
        onCancel={() => {
          setPasswordModalOpen(false);
          passwordForm.resetFields();
        }}
        onOk={() => passwordForm.submit()}
      >
        <Form form={passwordForm} layout="vertical" onFinish={handleChangePassword}>
          <Form.Item
            name="new_password"
            label="New Password"
            rules={[
              { required: true, message: 'Please enter new password' },
              { min: 6, message: 'Password must be at least 6 characters' }
            ]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminPortal;
