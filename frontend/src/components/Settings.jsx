import React, { useEffect, useState } from 'react';
import { Card, Col, Form, Input, Row, Select, Space, Typography, Button, Divider, message, Tabs } from 'antd';
import { KeyOutlined, LinkOutlined, SafetyCertificateOutlined, SettingOutlined } from '@ant-design/icons';
import axios from 'axios';

import { API_URL } from '../constants';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

const defaultSettings = {
  jenkins_url: '',
  jenkins_username: '',
  jenkins_api_token: '',
  ai_provider: 'litellm',
  ai_base_url: 'https://litellm.ai-server.fortiappsec.com',
  ai_api_key: 'sk-a122sVi4BhKo8XhtRx3Epg',
  ai_model: 'qwen3-235b-a22b',
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
        <Tabs defaultActiveKey="1" size="middle">
          <TabPane tab={<span><SettingOutlined /> Jenkins</span>} key="1">
            <Card>
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item label="Jenkins URL" name="jenkins_url" tooltip="Base URL of your Jenkins server (e.g. https://jenkins.example.com)">
                    <Input prefix={<LinkOutlined />} placeholder="https://jenkins.example.com" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="Username" name="jenkins_username" tooltip="User account with permissions to trigger and monitor builds">
                    <Input placeholder="jenkins-bot" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="API Token / Password" name="jenkins_api_token" tooltip="Stored securely on the server and sent with Jenkins API requests">
                    <Input.Password prefix={<KeyOutlined />} placeholder="Enter your API token" />
                  </Form.Item>
                </Col>
              </Row>
              <Text type="secondary">Settings are securely stored on the server and shared across Mobile Test Pilot services.</Text>
            </Card>
          </TabPane>

          <TabPane tab={<span><SafetyCertificateOutlined /> AI</span>} key="2">
            <Card>
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Form.Item label="Provider" name="ai_provider" tooltip="Private AI provider for internal analysis">
                    <Select
                      options={[
                        { label: 'Anthropic Claude (Private)', value: 'claude' },
                        { label: 'OpenAI GPT (Private)', value: 'openai' },
                        { label: 'Ollama (Local)', value: 'ollama' },
                      ]}
                      placeholder="Select a private AI provider"
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="AI Base URL" name="ai_base_url" tooltip="Endpoint for your private AI provider (e.g. https://your-private-ai.internal/v1)">
                    <Input placeholder="https://your-private-ai.internal/v1" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="API Key" name="ai_api_key" tooltip="API key for authenticating with your private AI service">
                    <Input.Password prefix={<KeyOutlined />} placeholder="Enter your private API key" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="Model" name="ai_model" tooltip="Preferred model for AI-powered workflows">
                    <Input placeholder="Enter model name (e.g., qwen3-235b-a22b)" />
                  </Form.Item>
                </Col>
              </Row>
              <Text type="secondary">Configure your private AI service for internal test analysis and insights.</Text>
            </Card>
          </TabPane>

          <TabPane tab={<span><SettingOutlined /> General</span>} key="3">
            <Card>
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
            </Card>
          </TabPane>
        </Tabs>

        <Divider />
        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="primary" htmlType="submit" loading={loading}>Save Settings</Button>
        </Space>
      </Form>
    </div>
  );
}

export default Settings;