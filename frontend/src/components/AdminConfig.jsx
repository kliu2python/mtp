import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, message, Tabs, Space, Alert, Tag, Popconfirm, Divider, Switch, Table as AntTable, InputNumber } from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const AdminConfig = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [androidForm] = Form.useForm();
  const [iosForm] = Form.useForm();
  const [loginForm] = Form.useForm();
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [adminToken, setAdminToken] = useState(null);

  // Release test config state
  const [versions, setVersions] = useState([]);
  const [versionInput, setVersionInput] = useState('');

  // Android and iOS version lists
  const [androidVersions, setAndroidVersions] = useState([]);
  const [iosVersions, setIosVersions] = useState([]);
  const [androidVersionInput, setAndroidVersionInput] = useState('');
  const [iosVersionInput, setIosVersionInput] = useState('');
  const [disabledVersions, setDisabledVersions] = useState([]);

  // Version build number ranges (for release cycles)
  const [versionRanges, setVersionRanges] = useState([]);
  // Version options for dropdown
  const [versionOptions, setVersionOptions] = useState([]);
  // New version range input
  const [newVersion, setNewVersion] = useState('');
  const [newAndroidMin, setNewAndroidMin] = useState('');
  const [newAndroidMax, setNewAndroidMax] = useState('');
  const [newIosMin, setNewIosMin] = useState('');
  const [newIosMax, setNewIosMax] = useState('');

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
      loadReleaseTestConfig();
    } catch (error) {
      console.error('Error loading default payloads:', error);
      message.error('Failed to load default payloads');
    } finally {
      setLoading(false);
    }
  };

  const loadReleaseTestConfig = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/release-test-config`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`
        }
      });
      const config = response.data;
      const allVersions = config.versions || [];
      const disabledVersions = config.disabled_versions || [];
      const versionBuildNumbers = config.version_build_numbers || [];

      // Separate Android and iOS versions
      const androidVers = allVersions.filter(v => v.startsWith('android_'));
      const iosVers = allVersions.filter(v => v.startsWith('ios_'));

      setAndroidVersions(androidVers);
      setIosVersions(iosVers);
      setVersions(allVersions);
      setDisabledVersions(disabledVersions);

      // Merge Android and iOS ranges by version
      const mergedRanges = [];
      const versionSet = new Set(versionBuildNumbers.map(v => v.version));
      versionSet.forEach(version => {
        const androidRange = versionBuildNumbers.find(r => r.version === version && r.platform === 'android');
        const iosRange = versionBuildNumbers.find(r => r.version === version && r.platform === 'ios');
        mergedRanges.push({
          version,
          min_build_number: androidRange?.min_build_number || '',
          max_build_number: androidRange?.max_build_number || '',
          ios_min_build_number: iosRange?.min_build_number || '',
          ios_max_build_number: iosRange?.max_build_number || ''
        });
      });
      setVersionRanges(mergedRanges);

      // Extract unique version numbers for options
      const versionNums = [...new Set(versionBuildNumbers.map(v => v.version))];
      setVersionOptions(versionNums.map(v => ({ label: v, value: v })));
    } catch (error) {
      console.error('Error loading release test config:', error);
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

  // Release Test Config functions - Android versions
  const handleAddAndroidVersion = () => {
    let version = androidVersionInput.trim();
    if (!version) {
      message.error('Please enter an Android version');
      return;
    }
    // Auto-add prefix if missing
    if (!version.startsWith('android_')) {
      version = `android_${version}`;
    }
    if (androidVersions.includes(version)) {
      message.error('Version already exists');
      return;
    }
    setAndroidVersions([...androidVersions, version]);
    setVersions([...versions, version]);
    setAndroidVersionInput('');
  };

  const handleRemoveAndroidVersion = (versionToRemove) => {
    setAndroidVersions(androidVersions.filter(v => v !== versionToRemove));
    setVersions(versions.filter(v => v !== versionToRemove));
  };

  // Release Test Config functions - iOS versions
  const handleAddIosVersion = () => {
    let version = iosVersionInput.trim();
    if (!version) {
      message.error('Please enter an iOS version');
      return;
    }
    // Auto-add prefix if missing
    if (!version.startsWith('ios_')) {
      version = `ios_${version}`;
    }
    if (iosVersions.includes(version)) {
      message.error('Version already exists');
      return;
    }
    setIosVersions([...iosVersions, version]);
    setVersions([...versions, version]);
    setIosVersionInput('');
  };

  const handleRemoveIosVersion = (versionToRemove) => {
    setIosVersions(iosVersions.filter(v => v !== versionToRemove));
    setVersions(versions.filter(v => v !== versionToRemove));
  };

  // Toggle version enable/disable
  const handleToggleVersion = (version, enabled) => {
    if (enabled) {
      // Enable: remove from disabledVersions
      setDisabledVersions(disabledVersions.filter(v => v !== version));
    } else {
      // Disable: add to disabledVersions if not already there
      if (!disabledVersions.includes(version)) {
        setDisabledVersions([...disabledVersions, version]);
      }
    }
  };

  // Version Build Number Range functions
  const handleAddVersionRange = () => {
    if (!newVersion.trim()) {
      message.error('Please enter a version');
      return;
    }

    const hasAndroid = newAndroidMin.trim() && newAndroidMax.trim();
    const hasIos = newIosMin.trim() && newIosMax.trim();

    if (!hasAndroid && !hasIos) {
      message.error('Please enter at least Android or iOS build number range');
      return;
    }

    // Check if version already exists
    const existingIndex = versionRanges.findIndex(r => r.version === newVersion);

    const newRange = {
      version: newVersion,
      min_build_number: hasAndroid ? newAndroidMin : '',
      max_build_number: hasAndroid ? newAndroidMax : '',
      ios_min_build_number: hasIos ? newIosMin : '',
      ios_max_build_number: hasIos ? newIosMax : ''
    };

    if (existingIndex >= 0) {
      // Update existing - merge with existing values
      const existing = versionRanges[existingIndex];
      const updatedRange = {
        version: newVersion,
        min_build_number: hasAndroid ? newAndroidMin : existing.min_build_number,
        max_build_number: hasAndroid ? newAndroidMax : existing.max_build_number,
        ios_min_build_number: hasIos ? newIosMin : existing.ios_min_build_number,
        ios_max_build_number: hasIos ? newIosMax : existing.ios_max_build_number
      };
      const newRanges = [...versionRanges];
      newRanges[existingIndex] = updatedRange;
      setVersionRanges(newRanges);
    } else {
      // Add new
      setVersionRanges([...versionRanges, newRange]);
    }

    // Clear inputs
    setNewVersion('');
    setNewAndroidMin('');
    setNewAndroidMax('');
    setNewIosMin('');
    setNewIosMax('');

    message.success('Version range added/updated');
  };

  const handleRemoveVersionRange = (versionToRemove) => {
    setVersionRanges(versionRanges.filter(r => r.version !== versionToRemove));
    message.success('Version range removed');
  };

  const handleSaveReleaseTestConfig = async () => {
    try {
      setSaving(true);

      // Prepare version_build_numbers for backend
      const versionBuildNumbers = [];

      versionRanges.forEach(range => {
        // Add Android range if exists
        if (range.min_build_number && range.max_build_number) {
          versionBuildNumbers.push({
            version: range.version,
            platform: 'android',
            min_build_number: range.min_build_number,
            max_build_number: range.max_build_number
          });
        }
        // Add iOS range if exists
        if (range.ios_min_build_number && range.ios_max_build_number) {
          versionBuildNumbers.push({
            version: range.version,
            platform: 'ios',
            min_build_number: range.ios_min_build_number,
            max_build_number: range.ios_max_build_number
          });
        }
      });

      await axios.post(`${API_URL}/api/release-test-config`, {
        versions,
        disabled_versions: disabledVersions,
        version_build_numbers: versionBuildNumbers
      }, {
        headers: {
          'Authorization': `Bearer ${adminToken}`
        }
      });
      message.success('Release Test Configuration saved successfully');
    } catch (error) {
      console.error('Failed to save release test config:', error);
      message.error('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteReleaseTestConfig = async () => {
    try {
      setSaving(true);
      await axios.delete(`${API_URL}/api/release-test-config`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`
        }
      });
      setVersions([]);
      setBuildNumbers([]);
      setAndroidVersions([]);
      setIosVersions([]);
      setDisabledVersions([]);
      message.success('Configuration deleted successfully');
    } catch (error) {
      console.error('Failed to delete release test config:', error);
      message.error('Failed to delete configuration');
    } finally {
      setSaving(false);
    }
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
    },
    {
      key: 'releaseTestConfig',
      label: 'Release Test Config',
      children: (
        <div>
          <Alert
            message="Release Test Configuration"
            description="Configure allowed Android/iOS versions and build numbers for release tests. Users can only select from these configured values when starting new release tests."
            type="info"
            style={{ marginBottom: 16 }}
          />

          {/* Android Versions Section */}
          <div style={{ marginBottom: 24 }}>
            <h3>Android Versions</h3>
            <Space wrap style={{ marginBottom: 16 }}>
              {androidVersions.map(version => {
                const isDisabled = disabledVersions.includes(version);
                return (
                  <Tag
                    key={version}
                    closable
                    onClose={() => handleRemoveAndroidVersion(version)}
                    color={isDisabled ? 'default' : 'green'}
                    style={{ fontSize: 14, opacity: isDisabled ? 0.6 : 1 }}
                  >
                    {version.replace('android_', 'Android ')}
                    <Switch
                      size="small"
                      checked={!isDisabled}
                      onChange={(checked) => handleToggleVersion(version, checked)}
                      onClick={(e) => e.stopPropagation()}
                      style={{ marginLeft: 8 }}
                    />
                  </Tag>
                );
              })}
            </Space>
            <Space>
              <Input
                placeholder="e.g., android_15"
                value={androidVersionInput}
                onChange={(e) => setAndroidVersionInput(e.target.value)}
                onPressEnter={handleAddAndroidVersion}
                style={{ width: 200 }}
              />
              <Button icon={<PlusOutlined />} onClick={handleAddAndroidVersion}>
                Add Android Version
              </Button>
            </Space>
          </div>

          {/* iOS Versions Section */}
          <div style={{ marginBottom: 24 }}>
            <h3>iOS Versions</h3>
            <Space wrap style={{ marginBottom: 16 }}>
              {iosVersions.map(version => {
                const isDisabled = disabledVersions.includes(version);
                return (
                  <Tag
                    key={version}
                    closable
                    onClose={() => handleRemoveIosVersion(version)}
                    color={isDisabled ? 'default' : 'blue'}
                    style={{ fontSize: 14, opacity: isDisabled ? 0.6 : 1 }}
                  >
                    {version.replace('ios_', 'iOS ')}
                    <Switch
                      size="small"
                      checked={!isDisabled}
                      onChange={(checked) => handleToggleVersion(version, checked)}
                      onClick={(e) => e.stopPropagation()}
                      style={{ marginLeft: 8 }}
                    />
                  </Tag>
                );
              })}
            </Space>
            <Space>
              <Input
                placeholder="e.g., ios_16"
                value={iosVersionInput}
                onChange={(e) => setIosVersionInput(e.target.value)}
                onPressEnter={handleAddIosVersion}
                style={{ width: 200 }}
              />
              <Button icon={<PlusOutlined />} onClick={handleAddIosVersion}>
                Add iOS Version
              </Button>
            </Space>
          </div>

          {/* Version Build Number Ranges Section */}
          <div style={{ marginBottom: 24 }}>
            <h3>Version Build Number Ranges (for Release Cycles)</h3>
            <Alert
              message="Configure build number ranges for each version"
              description="Example: Version 6.4.0 Android has build numbers 0018-0022, iOS has 0023-0029. Version 6.3.0 can only use build numbers below 0023."
              type="info"
              style={{ marginBottom: 16 }}
            />

            {/* Version Range Table */}
            <AntTable
              dataSource={versionRanges}
              rowKey="version"
              pagination={false}
              size="small"
              style={{ marginBottom: 16 }}
              columns={[
                {
                  title: 'Version',
                  dataIndex: 'version',
                  key: 'version',
                  width: 150,
                },
                {
                  title: 'Android Min',
                  dataIndex: 'min_build_number',
                  key: 'min_build_number',
                  width: 100,
                },
                {
                  title: 'Android Max',
                  dataIndex: 'max_build_number',
                  key: 'max_build_number',
                  width: 100,
                },
                {
                  title: 'iOS Min',
                  dataIndex: 'ios_min_build_number',
                  key: 'ios_min_build_number',
                  width: 100,
                },
                {
                  title: 'iOS Max',
                  dataIndex: 'ios_max_build_number',
                  key: 'ios_max_build_number',
                  width: 100,
                },
                {
                  title: 'Actions',
                  key: 'actions',
                  width: 100,
                  render: (_, record) => (
                    <Button
                      danger
                      size="small"
                      onClick={() => handleRemoveVersionRange(record.version)}
                    >
                      Delete
                    </Button>
                  ),
                },
              ]}
            />

            {/* Add Version Range Form */}
            <Space wrap>
              <Input
                placeholder="Version (e.g., 6.4.0)"
                value={newVersion}
                onChange={(e) => setNewVersion(e.target.value)}
                style={{ width: 120 }}
              />
              <Input
                placeholder="Android Min (e.g., 0018)"
                value={newAndroidMin}
                onChange={(e) => setNewAndroidMin(e.target.value)}
                style={{ width: 100 }}
              />
              <Input
                placeholder="Android Max (e.g., 0022)"
                value={newAndroidMax}
                onChange={(e) => setNewAndroidMax(e.target.value)}
                style={{ width: 100 }}
              />
              <Input
                placeholder="iOS Min (e.g., 0023)"
                value={newIosMin}
                onChange={(e) => setNewIosMin(e.target.value)}
                style={{ width: 100 }}
              />
              <Input
                placeholder="iOS Max (e.g., 0029)"
                value={newIosMax}
                onChange={(e) => setNewIosMax(e.target.value)}
                style={{ width: 100 }}
              />
              <Button icon={<PlusOutlined />} onClick={handleAddVersionRange}>
                Add/Update Range
              </Button>
            </Space>
          </div>

          <Divider />

          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSaveReleaseTestConfig}
              loading={saving}
            >
              Save Configuration
            </Button>
            <Popconfirm
              title="Delete Configuration"
              description="Are you sure you want to delete this configuration?"
              onConfirm={handleDeleteReleaseTestConfig}
              okText="Delete"
              cancelText="Cancel"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        </div>
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
