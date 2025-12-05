import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Select,
  Space,
  Table,
  Tabs,
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

const { Title, Text, Paragraph } = Typography;

const buildMantisLink = (issue) => issue?.url || `${API_URL}/mantis/view.php?id=${issue?.issue_id || issue?.id}`;

const defaultPagination = {
  pageSize: 5,
  showSizeChanger: true,
  pageSizeOptions: ['5', '10', '20'],
};

const PreFlightSection = ({
  platform,
  accent,
  fileAccept,
  entries,
  onAddEntry,
  mantisOptions,
  mantisLoading,
  jenkinsUrl,
  pageSize,
  onPageSizeChange,
}) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState([]);

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
        width: 160,
        render: (_, record) => (
          <Button
            type="link"
            icon={<CloudDownloadOutlined />}
            href={record.downloadUrl}
            download={record.fileName}
          >
            Download App
          </Button>
        ),
      },
    ],
    [jenkinsUrl],
  );

  const handleSubmit = (values) => {
    if (fileList.length === 0) {
      message.error('Please upload the application file before submitting.');
      return;
    }

    const selectedIssues = mantisOptions.filter((issue) => values.mantisIds?.includes(issue.value));
    const primaryFile = fileList[0];
    const file = primaryFile.originFileObj || primaryFile;

    const downloadUrl = URL.createObjectURL(file);

    onAddEntry({
      fileName: primaryFile.name,
      buildNumber: values.buildNumber,
      mantis: selectedIssues.map((issue) => ({ ...issue, url: buildMantisLink(issue) })),
      downloadUrl,
      jenkinsUrl,
    });

    message.success(`${platform} entry added to Acceptable Tests.`);
    form.resetFields();
    setFileList([]);
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <UploadOutlined style={{ color: accent }} />
            <span>Submit {platform} Build for Acceptable Test</span>
          </Space>
        }
        extra={
          <Button type="text" icon={<ReloadOutlined />} onClick={() => form.resetFields()}>
            Reset
          </Button>
        }
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
              <p className="ant-upload-hint">The file will be used directly for acceptable testing.</p>
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
            <Button type="primary" htmlType="submit" icon={<SafetyCertificateOutlined />}>
              Add to Acceptable Test List
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title={
          <Space>
            <LinkOutlined />
            <span>{platform} Acceptable Tests</span>
          </Space>
        }
      >
        <Table
          dataSource={entries}
          columns={columns}
          rowKey="id"
          pagination={{
            ...defaultPagination,
            pageSize,
            onShowSizeChange: (_, size) => onPageSizeChange(size),
          }}
        />
      </Card>
    </Space>
  );
};

const PreFlight = ({ jenkinsUrl }) => {
  const [mantisOptions, setMantisOptions] = useState([]);
  const [mantisLoading, setMantisLoading] = useState(false);
  const [entries, setEntries] = useState({ ios: [], android: [] });
  const [pageSizes, setPageSizes] = useState({ ios: 5, android: 5 });

  const fetchResolvedIssues = async () => {
    setMantisLoading(true);
    try {
      const { data } = await axios.get(`${API_URL}/api/mantis/`, {
        params: {
          status: 'resolved',
          page_size: 100,
          page: 1,
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

  useEffect(() => {
    fetchResolvedIssues();
  }, []);

  const handleAddEntry = (platform, payload) => {
    setEntries((prev) => ({
      ...prev,
      [platform]: [
        {
          id: `${platform}-${Date.now()}`,
          ...payload,
        },
        ...prev[platform],
      ],
    }));
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
          accent="#1f7ae0"
          fileAccept=".ipa"
          mantisOptions={mantisOptions}
          mantisLoading={mantisLoading}
          entries={entries.ios}
          onAddEntry={(payload) => handleAddEntry('ios', payload)}
          jenkinsUrl={jenkinsUrl}
          pageSize={pageSizes.ios}
          onPageSizeChange={(size) => setPageSizes((prev) => ({ ...prev, ios: size }))}
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
          accent="#52c41a"
          fileAccept=".apk"
          mantisOptions={mantisOptions}
          mantisLoading={mantisLoading}
          entries={entries.android}
          onAddEntry={(payload) => handleAddEntry('android', payload)}
          jenkinsUrl={jenkinsUrl}
          pageSize={pageSizes.android}
          onPageSizeChange={(size) => setPageSizes((prev) => ({ ...prev, android: size }))}
        />
      ),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <div>
        <Title level={3} style={{ marginBottom: 4 }}>
          PreFlight Acceptable Test
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Prepare builds for QA by uploading platform binaries, tagging fixed Mantis issues, and tracking acceptable tests in one place.
        </Paragraph>
      </div>

      {!jenkinsUrl && (
        <Alert
          type="info"
          showIcon
          message="Jenkins link not configured"
          description="Add a Jenkins URL in Settings to enable quick access from the Acceptable Test table."
        />
      )}

      <Tabs items={tabItems} />
    </Space>
  );
};

export default PreFlight;
