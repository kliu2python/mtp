import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, message, Tabs, Space, Alert, Typography } from 'antd';
import axios from 'axios';
import { API_URL } from '../constants';

const { Text } = Typography;

const AdminConfig = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [androidForm] = Form.useForm();
  const [iosForm] = Form.useForm();
  const [loginForm] = Form.useForm();
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [adminToken, setAdminToken] = useState(null);

  // Check if already logged in
  useEffect(() => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      setAdminToken(token);
      setIsAdminLoggedIn(true);
      loadDefaultPayloads();
    }
  }, []);

  const loadDefaultPayloads = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/admin/default-payloads`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`
        }
      });

      if (response.data.android) {
        androidForm.setFieldsValue(response.data.android);
      }
      if (response.data.ios) {
        iosForm.setFieldsValue(response.data.ios);
      }
    } catch (error) {
      console.error('Error loading default payloads:', error);
      message.error('Failed to load default payloads');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (values) => {
    try {
      setSaving(true);
      const response = await axios.post(`${API_URL}/api/admin/login`, {
        username: values.username,
        password: values.password
      });

      if (response.data.access_token) {
        setAdminToken(response.data.access_token);
        localStorage.setItem('adminToken', response.data.access_token);
        setIsAdminLoggedIn(true);
        message.success('Admin login successful');
        setShowLogin(false);
        loginForm.resetFields();
        loadDefaultPayloads();
      }
    } catch (error) {
      message.error('Invalid admin credentials');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    setAdminToken(null);
    setIsAdminLoggedIn(false);
    message.success('Logged out');
  };

  const handleSavePayload = async (platform, values) => {
    try {
      setSaving(true);
      const configKey = `${platform}_default_payload`;

      await axios.post(`${API_URL}/api/admin/config`, {
        config_key: configKey,
        config_value: values,
        description: `Default payload for ${platform} Jenkins jobs`
      }, {
        headers: {
          'Authorization': `Bearer ${adminToken}`
        }
      });

      message.success(`${platform.toUpperCase()} default payload saved successfully`);
    } catch (error) {
      console.error('Error saving payload:', error);
      message.error('Failed to save payload');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAndroid = () => {
    androidForm.validateFields().then(values => {
      handleSavePayload('android', values);
    });
  };

  const handleSaveIos = () => {
    iosForm.validateFields().then(values => {
      handleSavePayload('ios', values);
    });
  };

  const handleResetAndroid = () => {
    androidForm.resetFields();
    handleSavePayload('android', {});
  };

  const handleResetIos = () => {
    iosForm.resetFields();
    handleSavePayload('ios', {});
  };

  if (!isAdminLoggedIn) {
    return (
      <Card title="Admin Configuration" style={{ maxWidth: 600, margin: '0 auto' }}>
        <Alert
          message="Admin Access Required"
          description="This page is for configuring default Jenkins payloads. Please login with admin credentials."
          type="warning"
          style={{ marginBottom: 24 }}
        />

        {!showLogin && (
          <Button
            type="primary"
            onClick={() => setShowLogin(true)}
            style={{ marginBottom: 16 }}
          >
            Admin Login
          </Button>
        )}

        {showLogin && (
          <Form form={loginForm} layout="vertical" onFinish={handleLogin}>
            <Form.Item
              name="username"
              label="Username"
              rules={[{ required: true, message: 'Please enter username' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true, message: 'Please enter password' }]}
            >
              <Input.Password />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={saving}>
                  Login
                </Button>
                <Button onClick={() => setShowLogin(false)}>
                  Cancel
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}
      </Card>
    );
  }

  const tabItems = [
    {
      key: 'android',
      label: 'Android Default Payload',
      children: (
        <Form form={androidForm} layout="vertical">
          <Alert
            message="Android Jenkins Job Configuration"
            description="These values will be used as default parameters when triggering Android Jenkins jobs. The ftm_apk_version is auto-generated based on build number."
            type="info"
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="docker_tag"
            name="docker_tag"
            tooltip="Docker image tag (default: debug_ftm_auto_latest)"
          >
            <Input placeholder="debug_ftm_auto_latest" />
          </Form.Item>

          <Form.Item
            label="mobile_emulator"
            name="mobile_emulator"
            tooltip="Emulator type"
          >
            <Input placeholder="google_api" />
          </Form.Item>

          <Form.Item
            label="RUN_STAGE"
            name="RUN_STAGE"
            tooltip="Test execution stage"
          >
            <Input placeholder="ALL" />
          </Form.Item>

          <Form.Item
            label="dns"
            name="dns"
            tooltip="DNS server (optional, can be overridden per request)"
          >
            <Input placeholder="10.160.41.22 or null" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                onClick={handleSaveAndroid}
                loading={saving}
              >
                Save Android Payload
              </Button>
              <Button onClick={handleResetAndroid}>
                Reset to Default
              </Button>
            </Space>
          </Form.Item>
        </Form>
      )
    },
    {
      key: 'ios',
      label: 'iOS Default Payload',
      children: (
        <Form form={iosForm} layout="vertical">
          <Alert
            message="iOS Jenkins Job Configuration"
            description="These values will be used as default parameters when triggering iOS Jenkins jobs. The ftm_ipa_version is auto-generated based on build number."
            type="info"
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="docker_tag"
            name="docker_tag"
            tooltip="Docker image tag (default: debug_ftm_auto_latest)"
          >
            <Input placeholder="debug_ftm_auto_latest" />
          </Form.Item>

          <Form.Item
            label="RUN_STAGE"
            name="RUN_STAGE"
            tooltip="Test execution stage"
          >
            <Input placeholder="ALL" />
          </Form.Item>

          <Form.Item
            label="dns"
            name="dns"
            tooltip="DNS server (optional, can be overridden per request)"
          >
            <Input placeholder="10.160.41.22 or null" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                onClick={handleSaveIos}
                loading={saving}
              >
                Save iOS Payload
              </Button>
              <Button onClick={handleResetIos}>
                Reset to Default
              </Button>
            </Space>
          </Form.Item>
        </Form>
      )
    }
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Card
        title="Admin Configuration - Default Payloads"
        extra={
          <Button onClick={handleLogout}>
            Logout
          </Button>
        }
      >
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
};

export default AdminConfig;
