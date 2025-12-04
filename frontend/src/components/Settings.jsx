import React, { useEffect } from 'react';
import { Card, Col, Form, Input, Row, Select, Space, Typography, Button, Divider, message } from 'antd';
import { KeyOutlined, LinkOutlined, SafetyCertificateOutlined, SettingOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const SETTINGS_STORAGE_KEY = 'mtpSettings';

const defaultSettings = {
  jenkinsUrl: '',
  jenkinsUsername: '',
  jenkinsApiToken: '',
  aiBaseUrl: '',
  aiApiKey: '',
  aiModel: 'gpt-4.1',
  artifactStoragePath: '/var/lib/mtp/artifacts',
  notificationEmail: '',
};

function Settings() {
  const [form] = Form.useForm();

  useEffect(() => {
    const storedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (storedSettings) {
      try {
        const parsed = JSON.parse(storedSettings);
        form.setFieldsValue({ ...defaultSettings, ...parsed });
      } catch (error) {
        console.error('Failed to parse stored settings', error);
      }
    } else {
      form.setFieldsValue(defaultSettings);
    }
  }, [form]);

  const handleSubmit = (values) => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(values));
    message.success('Settings updated successfully');
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
              <Form.Item label="Jenkins URL" name="jenkinsUrl" tooltip="Base URL of your Jenkins server (e.g. https://jenkins.example.com)">
                <Input prefix={<LinkOutlined />} placeholder="https://jenkins.example.com" />
              </Form.Item>
              <Form.Item label="Username" name="jenkinsUsername" tooltip="User account with permissions to trigger and monitor builds">
                <Input placeholder="jenkins-bot" />
              </Form.Item>
              <Form.Item label="API Token / Password" name="jenkinsApiToken" tooltip="Stored locally and sent with Jenkins API requests">
                <Input.Password prefix={<KeyOutlined />} placeholder="Enter your API token" />
              </Form.Item>
              <Text type="secondary">Credentials are stored in your browser only and are not shared with our servers.</Text>
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title={<Space><SafetyCertificateOutlined /> <span>AI Provider</span></Space>}>
              <Form.Item label="AI Base URL" name="aiBaseUrl" tooltip="Endpoint for your AI provider (e.g. https://api.openai.com/v1)">
                <Input placeholder="https://api.openai.com/v1" />
              </Form.Item>
              <Form.Item label="API Key" name="aiApiKey" tooltip="Used for requests to generate test plans, scripts, or summaries">
                <Input.Password prefix={<KeyOutlined />} placeholder="Enter your API key" />
              </Form.Item>
              <Form.Item label="Model" name="aiModel" tooltip="Preferred model for AI-powered workflows">
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
              <Form.Item label="Artifact Storage Path" name="artifactStoragePath" tooltip="Directory used for build artifacts, logs, and reports">
                <Input prefix={<LinkOutlined />} placeholder="/var/lib/mtp/artifacts" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="Notification Email" name="notificationEmail" tooltip="Address that should receive system alerts and summaries">
                <Input placeholder="qa-team@example.com" />
              </Form.Item>
            </Col>
          </Row>
          <Divider />
          <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="primary" htmlType="submit">Save Settings</Button>
          </Space>
        </Card>
      </Form>
    </div>
  );
}

export default Settings;
