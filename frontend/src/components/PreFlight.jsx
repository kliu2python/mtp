import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import {
  ApartmentOutlined,
  AndroidOutlined,
  CloudDownloadOutlined,
  LinkOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { Title, Text } = Typography;

const buildMantisLink = (issue) => issue?.url || `https://mantis.fortinet.com/bug_view_page.php?bug_id=${issue?.issue_id || issue?.id}`;

const defaultPagination = {
  pageSize: 5,
  showSizeChanger: true,
  pageSizeOptions: ['5', '10', '20'],
};

const buildFileUrl = (path) => {
  if (!path) return '';
  const base = API_URL?.replace(/\/$/, '') || '';
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
};

const PreFlightSection = ({
  platform,
  platformKey,
  accent,
  fileAccept,
  entries,
  onAddEntry,
  onDeleteEntry,
  onRefresh,
  mantisOptions,
  mantisLoading,
  jenkinsUrl,
  pageSize,
  onPageSizeChange,
  recordLoading,
}) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const columns = useMemo(
    () => [
      {
        title: 'App File',
        dataIndex: 'fileName',
        key: 'fileName',
      },
      {
        title: 'Build Number',
        dataIndex: 'buildNumber',
        key: 'buildNumber',
        width: 160,
      },
      {
        title: 'Result',
        dataIndex: 'status',
        key: 'status',
        width: 130,
        render: (status) => {
          const normalized = (status || 'running').toString().toUpperCase();
          const colorMap = {
            SUCCESS: 'green',
            FAILURE: 'red',
            ABORTED: 'volcano',
            UNSTABLE: 'orange',
            NOT_BUILT: 'default',
            RUNNING: 'blue',
          };
          return <Tag color={colorMap[normalized] || 'blue'}>{normalized}</Tag>;
        },
      },
      {
        title: 'Resolved Mantis IDs',
        dataIndex: 'mantis',
        key: 'mantis',
        render: (mantis = []) => (
          <Space size={[8, 8]} wrap>
            {mantis.map((issue) => (
              <a key={issue.value} href={issue.url} target="_blank" rel="noreferrer">
                #{issue.value}
              </a>
            ))}
          </Space>
        ),
      },
      {
        title: 'Jenkins Job',
        dataIndex: 'jenkinsUrl',
        key: 'jenkinsUrl',
        render: (url) =>
          url ? (
            <a href={url} target="_blank" rel="noreferrer">
              View Job
            </a>
          ) : (
            <Text type="secondary">Not configured</Text>
          ),
        width: 160,
      },
      {
        title: 'Actions',
        key: 'actions',
        width: 220,
        render: (_, record) => (
          <Space size="small">
            {record.downloadUrl ? (
              <Button
                type="link"
                icon={<CloudDownloadOutlined />}
                href={record.downloadUrl}
                download={record.fileName}
              >
                Download App
              </Button>
            ) : (
              <Text type="secondary">No download available</Text>
            )}
            <Popconfirm
              title="Delete this acceptable test record?"
              okText="Delete"
              cancelText="Cancel"
              disabled={!record.rawId && !record.name}
              onConfirm={() => onDeleteEntry(record)}
            >
              <Button type="link" danger disabled={!record.rawId && !record.name}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [jenkinsUrl, onDeleteEntry],
  );

  const handleSubmit = async (values) => {
    if (fileList.length === 0) {
      message.error('Please upload the application file before submitting.');
      return;
    }

    const selectedIssues = mantisOptions.filter((issue) => values.mantisIds?.includes(issue.value));
    const primaryFile = fileList[0];
    const file = primaryFile.originFileObj || primaryFile;

    try {
      setSubmitting(true);

      const formData = new FormData();
      formData.append('files', file);

      const uploadResponse = await axios.post(`${API_URL}/api/files/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const uploadedFile = uploadResponse?.data?.files?.[0];
      const downloadUrl = buildFileUrl(uploadedFile?.path);

      if (!downloadUrl) {
        message.error('Unable to determine download URL for the uploaded app.');
        return;
      }

      const payload = {
        environment: 'Prod',
        platforms: [platformKey === 'ios' ? 'ios16' : 'android15'],
        parameters: {
          RUN_STAGE: 'FortiGate',
          mantis_ids: values.mantisIds,
          build_number: values.buildNumber,
          app_download_url: downloadUrl,
          [platformKey === 'ios' ? 'ftm_ipa_version' : 'ftm_apk_version']: file.name,
        },
        test_scope: 'acceptable',
      };

      try {
        await axios.post(`${API_URL}/api/jenkins/run/execute/ftm`, payload);
        message.success('PreFlight check triggered successfully.');
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Failed to trigger PreFlight check', error);
        const errorMsg = error?.response?.data?.error || error?.response?.data?.detail;
        message.error(errorMsg || 'Unable to trigger PreFlight check.');
        return;
      }

      onAddEntry({
        fileName: primaryFile.name,
        buildNumber: values.buildNumber,
        mantis: selectedIssues.map((issue) => ({ ...issue, url: buildMantisLink(issue) })),
        downloadUrl,
        jenkinsUrl,
        status: 'RUNNING',
        platform: platformKey,
      });

      message.success(`${platform} PreFlight check recorded.`);
      form.resetFields();
      setFileList([]);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to record PreFlight check', error);
      message.error('Unable to record PreFlight check. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Row gutter={[16, 16]} align="top">
      <Col xs={24} lg={9}>
        <Card
          size="small"
          title={
            <Space>
              <UploadOutlined style={{ color: accent }} />
              <Text strong style={{ fontSize: 14 }}>Submit {platform} Build for PreFlight Check</Text>
            </Space>
          }
          extra={
            <Button type="text" icon={<ReloadOutlined />} onClick={() => form.resetFields()}>
              Reset
            </Button>
          }
          bodyStyle={{ padding: 16 }}
        >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            name="appFile"
            label={`${platform} App File`}
            rules={[{ required: true, message: 'Please upload the build artifact.' }]}
          >
            <Upload.Dragger
              accept={fileAccept}
              multiple={false}
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: next }) => setFileList(next)}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">Click or drag {platform} build here</p>
              <p className="ant-upload-hint">The file will be used directly for the PreFlight check.</p>
            </Upload.Dragger>
          </Form.Item>

          <Form.Item
            name="buildNumber"
            label="Build Number"
            rules={[{ required: true, message: 'Please enter the build number.' }]}
          >
            <Input placeholder="e.g., 1.2.3" />
          </Form.Item>

          <Form.Item
            name="mantisIds"
            label="Fixed Mantis Numbers"
            rules={[{ required: true, message: 'Select at least one resolved Mantis issue.' }]}
          >
            <Select
              mode="multiple"
              placeholder="Select resolved issues"
              loading={mantisLoading}
              options={mantisOptions}
              optionFilterProp="label"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SafetyCertificateOutlined />}
              loading={submitting}
            >
              Run PreFlight Check
            </Button>
          </Form.Item>
        </Form>
        </Card>
      </Col>

      <Col xs={24} lg={15}>
        <Card
          size="small"
          title={
            <Space>
              <LinkOutlined />
              <Text strong style={{ fontSize: 14 }}>{platform} PreFlight Checks</Text>
            </Space>
          }
          extra={
            <Button type="text" icon={<ReloadOutlined />} onClick={onRefresh}>
              Refresh
            </Button>
          }
          bodyStyle={{ padding: 12 }}
        >
          <Table
            size="small"
            dataSource={entries}
            columns={columns}
            rowKey="id"
            loading={recordLoading}
            pagination={{
              ...defaultPagination,
              pageSize,
              onShowSizeChange: (_, size) => onPageSizeChange(size),
            }}
          />
        </Card>
      </Col>
    </Row>
  );
};

const PreFlight = ({ jenkinsUrl }) => {
  const [mantisOptions, setMantisOptions] = useState([]);
  const [mantisLoading, setMantisLoading] = useState(false);
  const [entries, setEntries] = useState({ ios: [], android: [] });
  const [pageSizes, setPageSizes] = useState({ ios: 5, android: 5 });
  const [recordLoading, setRecordLoading] = useState(false);

  const fetchResolvedIssues = async () => {
    setMantisLoading(true);
    try {
      const { data } = await axios.get(`${API_URL}/api/mantis/all`, {
        params: {
          exclude_statuses: ['acknowledged', 'closed'],
          sort_by: 'last_updated',
          sort_order: 'desc',
        },
      });

      const issues = (data.issues || []).map((issue) => ({
        label: `#${issue.issue_id || issue.id} ${issue.summary || ''}`.trim(),
        value: issue.issue_id || issue.id,
        url: buildMantisLink(issue),
        summary: issue.summary,
      }));

      setMantisOptions(issues);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to load resolved Mantis issues', error);
      message.error('Unable to load resolved Mantis issues. Please try again later.');
    } finally {
      setMantisLoading(false);
    }
  };

  const fetchAcceptableRecords = async () => {
    setRecordLoading(true);
    try {
      const { data } = await axios.get(`${API_URL}/api/jenkins/run/acceptable-tests`);
      const records = data?.results || data || [];

      const normalized = records.reduce(
        (acc, record) => {
          const params = record.build_parameters || {};
          const platformKey = (record.platform || '').toLowerCase().includes('ios') ? 'ios' : 'android';
          const mantisIds =
            record.resolved_mantis_ids || record.mantis_ids || params.mantis_ids || [];
          const mantisEntries = Array.isArray(mantisIds)
            ? mantisIds.map((id) => ({
                value: id,
                label: `#${id}`,
                url: buildMantisLink({ issue_id: id }),
              }))
            : [];

          const buildNumber =
            record.build_number ||
            params.build_number ||
            params.buildNumber ||
            params.build ||
            params.build_num ||
            record.started_at ||
            'N/A';
          const downloadUrl = record.download_url || params.app_download_url || params.download_url;
          const fileName =
            record.app_file ||
            params.ftm_ipa_version ||
            params.ftm_apk_version ||
            params.ftm_ipa ||
            params.ftm_apk ||
            params.ftm_build_version ||
            params.ftm_build ||
            record.name ||
            'N/A';
          const rawId = record._id?.$oid || record._id;
          const recordId = rawId || record.name || `${platformKey}-${record.build_url || Date.now()}`;

          const entry = {
            id: recordId,
            rawId,
            name: record.name,
            platform: platformKey,
            fileName,
            buildNumber,
            mantis: mantisEntries,
            downloadUrl,
            jenkinsUrl: record.build_url,
            status: (record.res || record.status || 'RUNNING').toString().toUpperCase(),
          };

          acc[platformKey] = [...acc[platformKey], entry];
          return acc;
        },
        { ios: [], android: [] },
      );

      setEntries(normalized);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to load acceptable test records', error);
      message.error('Unable to load previous acceptable test records.');
    } finally {
      setRecordLoading(false);
    }
  };

  useEffect(() => {
    fetchResolvedIssues();
    fetchAcceptableRecords();
  }, []);

  const handleAddEntry = (platform, payload) => {
    setEntries((prev) => ({
      ...prev,
      [platform]: [
        {
          id: `${platform}-${Date.now()}`,
          platform,
          status: (payload.status || 'RUNNING').toString().toUpperCase(),
          ...payload,
        },
        ...prev[platform],
      ],
    }));
  };

  const handleDeleteEntry = async (platform, record) => {
    const recordId = record.rawId?.$oid || record.rawId || record.id;
    setRecordLoading(true);
    try {
      await axios.delete(`${API_URL}/api/jenkins/run/acceptable-tests`, {
        params: { id: recordId, name: record.name },
      });
      message.success('Acceptable test record deleted.');
      setEntries((prev) => ({
        ...prev,
        [platform]: prev[platform].filter((item) => item.id !== record.id),
      }));
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to delete acceptable test record', error);
      const errorMsg = error?.response?.data?.error;
      message.error(errorMsg || 'Unable to delete acceptable test record.');
    } finally {
      setRecordLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'ios',
      label: (
        <Space>
          <ApartmentOutlined />
          <span>FTM iOS</span>
        </Space>
      ),
      children: (
        <PreFlightSection
          platform="FTM iOS"
          platformKey="ios"
          accent="#1f7ae0"
          fileAccept=".ipa"
          mantisOptions={mantisOptions}
          mantisLoading={mantisLoading}
          entries={entries.ios}
          onAddEntry={(payload) => handleAddEntry('ios', payload)}
          onDeleteEntry={(record) => handleDeleteEntry('ios', record)}
          onRefresh={fetchAcceptableRecords}
          jenkinsUrl={jenkinsUrl}
          pageSize={pageSizes.ios}
          onPageSizeChange={(size) => setPageSizes((prev) => ({ ...prev, ios: size }))}
          recordLoading={recordLoading}
        />
      ),
    },
    {
      key: 'android',
      label: (
        <Space>
          <AndroidOutlined />
          <span>FTM Android</span>
        </Space>
      ),
      children: (
        <PreFlightSection
          platform="FTM Android"
          platformKey="android"
          accent="#52c41a"
          fileAccept=".apk"
          mantisOptions={mantisOptions}
          mantisLoading={mantisLoading}
          entries={entries.android}
          onAddEntry={(payload) => handleAddEntry('android', payload)}
          onDeleteEntry={(record) => handleDeleteEntry('android', record)}
          onRefresh={fetchAcceptableRecords}
          jenkinsUrl={jenkinsUrl}
          pageSize={pageSizes.android}
          onPageSizeChange={(size) => setPageSizes((prev) => ({ ...prev, android: size }))}
          recordLoading={recordLoading}
        />
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ marginBottom: 2, fontWeight: 600 }}>
          PreFlight Check
        </Title>
        <Text type="secondary" style={{ marginBottom: 0, fontSize: 13, display: 'block' }}>
          Prepare builds for QA by uploading platform binaries, tagging fixed Mantis issues, and triggering platform-specific PreFlight checks.
        </Text>
      </div>

      {!jenkinsUrl && (
        <Alert
          type="info"
          showIcon
          message="Jenkins link not configured"
          description="Add a Jenkins URL in Settings to enable quick access from the PreFlight check table."
        />
      )}

      <Tabs items={tabItems} />
    </Space>
  );
};

export default PreFlight;
