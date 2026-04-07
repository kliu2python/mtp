import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Space, message, Tag, Popconfirm, Divider, Switch, Table as AntTable, Alert } from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const ReleaseTestConfig = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState([]);
  const [versionInput, setVersionInput] = useState('');

  // Android and iOS version lists
  const [androidVersions, setAndroidVersions] = useState([]);
  const [iosVersions, setIosVersions] = useState([]);
  const [androidVersionInput, setAndroidVersionInput] = useState('');
  const [iosVersionInput, setIosVersionInput] = useState('');
  const [disabledVersions, setDisabledVersions] = useState([]);

  // Version build number ranges
  const [versionRanges, setVersionRanges] = useState([]);
  const [newVersion, setNewVersion] = useState('');
  const [newAndroidMin, setNewAndroidMin] = useState('');
  const [newAndroidMax, setNewAndroidMax] = useState('');
  const [newIosMin, setNewIosMin] = useState('');
  const [newIosMax, setNewIosMax] = useState('');

  // Default versions when config is not set
  const defaultVersions = [
    'android_15', 'android_14', 'android_13', 'android_12', 'android_11', 'android_10',
    'ios_26', 'ios_18', 'ios_17', 'ios_16', 'ios_15'
  ];

  // Fetch current config
  const fetchConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/release-test-config`);
      const data = response.data;
      const allVersions = data.versions?.length > 0 ? data.versions : defaultVersions;
      const disabledVers = data.disabled_versions || [];
      const versionBuildNumbers = data.version_build_numbers || [];

      // Separate Android and iOS versions
      const androidVers = allVersions.filter(v => v.startsWith('android_'));
      const iosVers = allVersions.filter(v => v.startsWith('ios_'));

      setAndroidVersions(androidVers);
      setIosVersions(iosVers);
      setVersions(allVersions);
      setDisabledVersions(disabledVers);

      // Merge Android and iOS ranges by version
      const mergedRanges = [];
      const versionSet = [...new Set(versionBuildNumbers.map(v => v.version))];
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
    } catch (error) {
      console.error('Failed to fetch config:', error);
      message.error('Failed to fetch configuration');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // Toggle version enable/disable
  const handleToggleVersion = (version, enabled) => {
    if (enabled) {
      setDisabledVersions(disabledVersions.filter(v => v !== version));
    } else {
      if (!disabledVersions.includes(version)) {
        setDisabledVersions([...disabledVersions, version]);
      }
    }
  };

  // Add Android version
  const handleAddAndroidVersion = () => {
    let version = androidVersionInput.trim();
    if (!version) {
      message.error('Please enter an Android version');
      return;
    }
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

  // Add iOS version
  const handleAddIosVersion = () => {
    let version = iosVersionInput.trim();
    if (!version) {
      message.error('Please enter an iOS version');
      return;
    }
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
      setVersionRanges([...versionRanges, {
        version: newVersion,
        min_build_number: hasAndroid ? newAndroidMin : '',
        max_build_number: hasAndroid ? newAndroidMax : '',
        ios_min_build_number: hasIos ? newIosMin : '',
        ios_max_build_number: hasIos ? newIosMax : ''
      }]);
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

  // Save configuration
  const handleSave = async () => {
    try {
      setLoading(true);

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
      });
      message.success('Configuration saved successfully');
    } catch (error) {
      console.error('Failed to save config:', error);
      message.error('Failed to save configuration');
    } finally {
      setLoading(false);
    }
  };

  // Delete configuration
  const handleDelete = async () => {
    try {
      setLoading(true);
      await axios.delete(`${API_URL}/api/release-test-config`);
      setVersions([]);
      setAndroidVersions([]);
      setIosVersions([]);
      setDisabledVersions([]);
      message.success('Configuration deleted successfully');
    } catch (error) {
      console.error('Failed to delete config:', error);
      message.error('Failed to delete configuration');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="Release Test Configuration"
        extra={
          <Space>
            <Button onClick={fetchConfig} loading={loading}>
              Refresh
            </Button>
            <Popconfirm
              title="Delete Configuration"
              description="Are you sure you want to delete this configuration?"
              onConfirm={handleDelete}
              okText="Delete"
              cancelText="Cancel"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={loading}
            >
              Save
            </Button>
          </Space>
        }
      >
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
        <div style={{ marginTop: 24, marginBottom: 24 }}>
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
      </Card>
    </div>
  );
};

export default ReleaseTestConfig;
