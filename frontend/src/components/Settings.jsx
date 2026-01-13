import React, { useEffect, useState } from 'react';
import { Card, Col, Form, Input, Row, Select, Space, Typography, Button, Divider, message } from 'antd';
import { KeyOutlined, LinkOutlined, SafetyCertificateOutlined, SettingOutlined } from '@ant-design/icons';
import axios from 'axios';

import { API_URL } from '../constants';

const { Title, Paragraph, Text } = Typography;

const defaultSettings = {
  jenkins_url: '',
  jenkins_username: '',
  jenkins_api_token: '',
  ai_provider: 'openai',
  ai_base_url: '',
  ai_api_key: '',
  ai_model: 'gpt-4.1',
  artifact_storage_path: '/var/lib/mtp/artifacts',
  notification_email: '',
};

function Settings({ onSettingsChange, initialSettings }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const normalizeSettings = (settings) => ({
    ...defaultSettings,
    ...settings,
  });

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API_URL}/api/settings`);
      const merged = normalizeSettings(data);
      form.setFieldsValue(merged);
      onSettingsChange?.(merged);
    } catch (error) {
      message.error('Failed to load saved settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialSettings) {
      form.setFieldsValue(normalizeSettings(initialSettings));
    } else {
      fetchSettings();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSettings]);

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const { data } = await axios.put(`${API_URL}/api/settings`, values);
      const merged = normalizeSettings(data);
      form.setFieldsValue(merged);
      onSettingsChange?.(merged);
      message.success('Settings updated successfully');
    } catch (error) {
      message.error('Failed to update settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={2} style={{ marginBottom: 8 }}>Settings</Title>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        Manage integration endpoints, credentials, and other important preferences used throughout the Mobile Test Pilot platform.
      </Paragraph>

      <Form
        form={form}
        layout="vertical"
        initialValues={defaultSettings}
        onFinish={handleSubmit}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title={<Space><SettingOutlined /> <span>Jenkins Integration</span></Space>}>
              <Form.Item label="Jenkins URL" name="jenkins_url" tooltip="Base URL of your Jenkins server (e.g. https://jenkins.example.com)">
                <Input prefix={<LinkOutlined />} placeholder="https://jenkins.example.com" />
              </Form.Item>
              <Form.Item label="Username" name="jenkins_username" tooltip="User account with permissions to trigger and monitor builds">
                <Input placeholder="jenkins-bot" />
              </Form.Item>
              <Form.Item label="API Token / Password" name="jenkins_api_token" tooltip="Stored securely on the server and sent with Jenkins API requests">
                <Input.Password prefix={<KeyOutlined />} placeholder="Enter your API token" />
              </Form.Item>
              <Text type="secondary">Settings are securely stored on the server and shared across Mobile Test Pilot services.</Text>
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title={<Space><SafetyCertificateOutlined /> <span>AI Provider</span></Space>}>
              <Form.Item label="Provider" name="ai_provider" tooltip="Provider used for AI-assisted authoring, remediation, and insights">
                <Select
                  options={[
                    { label: 'OpenAI', value: 'openai' },
                    { label: 'Anthropic Claude', value: 'claude' },
                    { label: 'Ollama', value: 'ollama' },
                  ]}
                  placeholder="Select a provider"
                />
              </Form.Item>
              <Form.Item label="AI Base URL" name="ai_base_url" tooltip="Endpoint for your AI provider (e.g. https://api.openai.com/v1)">
                <Input placeholder="https://api.openai.com/v1" />
              </Form.Item>
              <Form.Item label="API Key" name="ai_api_key" tooltip="Used for requests to generate test plans, scripts, or summaries">
                <Input.Password prefix={<KeyOutlined />} placeholder="Enter your API key" />
              </Form.Item>
              <Form.Item label="Model" name="ai_model" tooltip="Preferred model for AI-powered workflows">
                <Select
                  options={[
                    { label: 'gpt-4.1', value: 'gpt-4.1' },
                    { label: 'gpt-4o', value: 'gpt-4o' },
                    { label: 'gpt-3.5-turbo', value: 'gpt-3.5-turbo' },
                    { label: 'llama-3-70b', value: 'llama-3-70b' },
                  ]}
                  showSearch
                  filterOption={(input, option) => option?.label?.toLowerCase().includes(input.toLowerCase())}
                  placeholder="Select a model"
                />
              </Form.Item>
              <Text type="secondary">Configure the provider used by AI-assisted authoring, remediation, and insights.</Text>
            </Card>
          </Col>
        </Row>

        <Card style={{ marginTop: 16 }} title={<Space><SettingOutlined /> <span>General Preferences</span></Space>}>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Form.Item label="Artifact Storage Path" name="artifact_storage_path" tooltip="Directory used for build artifacts, logs, and reports">
                <Input prefix={<LinkOutlined />} placeholder="/var/lib/mtp/artifacts" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="Notification Email" name="notification_email" tooltip="Address that should receive system alerts and summaries">
                <Input placeholder="qa-team@example.com" />
              </Form.Item>
            </Col>
          </Row>
          <Divider />
          <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="primary" htmlType="submit" loading={loading}>Save Settings</Button>
          </Space>
        </Card>
      </Form>
    </div>
  );
}

export default Settings;
