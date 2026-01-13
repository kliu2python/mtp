import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CopyOutlined,
  LinkOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';
import { buildFileUrl, normalizeAcceptableRecords } from '../utils/acceptableTests';

const { Title, Text } = Typography;

const AcceptableTestDetail = () => {
  const navigate = useNavigate();
  const { platform, id } = useParams();
  const [loading, setLoading] = useState(true);
  const [record, setRecord] = useState(null);

  const shareLink = useMemo(() => `${window.location.origin}/preflight/acceptable/${platform}/${id}`, [platform, id]);

  const loadRecord = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API_URL}/api/jenkins/run/acceptable-tests`);
      const records = normalizeAcceptableRecords(data?.results || data || []);
      const match = records[platform]?.find((item) => item.id === id);
      setRecord(match || null);
      if (!match) {
        message.error('Acceptable test not found.');
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to load acceptable test detail', error);
      message.error('Unable to load acceptable test detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecord();
  }, [platform, id]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareLink);
      message.success('Share link copied to clipboard');
    } catch (error) {
      message.error('Unable to copy link.');
    }
  };

  if (loading) {
    return (
      <Space direction="vertical" style={{ width: '100%', alignItems: 'center', marginTop: 80 }}>
        <Spin tip="Loading acceptable test detail..." size="large" />
      </Space>
    );
  }

  if (!record) {
    return (
      <Alert
        message="Acceptable test not found"
        description="The requested acceptable test could not be located. It may have been deleted or the link is incorrect."
        type="error"
        action={
          <Button type="primary" onClick={() => navigate('/preflight')}>
            Back to PreFlight
          </Button>
        }
        showIcon
      />
    );
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/preflight')}>
            Back
          </Button>
          <div>
            <Title level={4} style={{ marginBottom: 0 }}>
              Acceptable Test Detail
            </Title>
            <Text type="secondary">Direct link to a single acceptable test record.</Text>
          </div>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadRecord}>
            Refresh
          </Button>
          <Button icon={<CopyOutlined />} onClick={handleCopy}>
            Copy Share Link
          </Button>
        </Space>
      </Space>

      <Card
        title={
          <Space>
            <LinkOutlined />
            <span>{record.fileName}</span>
          </Space>
        }
      >
        <Descriptions column={1} bordered size="middle" labelStyle={{ width: 200 }}>
          <Descriptions.Item label="Platform">{record.platform.toUpperCase()}</Descriptions.Item>
          <Descriptions.Item label="Status">
            <Tag color={record.status === 'SUCCESS' ? 'green' : record.status === 'FAILURE' ? 'red' : 'blue'}>
              {record.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Build Number">{record.buildNumber}</Descriptions.Item>
          <Descriptions.Item label="App File">{record.fileName}</Descriptions.Item>
          <Descriptions.Item label="Download">
            {record.downloadUrl ? (
              <a href={buildFileUrl(record.downloadUrl)} target="_blank" rel="noreferrer">
                Download Build
              </a>
            ) : (
              <Text type="secondary">Not available</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Jenkins Job">
            {record.jenkinsUrl ? (
              <a href={record.jenkinsUrl} target="_blank" rel="noreferrer">
                View in Jenkins
              </a>
            ) : (
              <Text type="secondary">Not configured</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Mantis Issues">
            {record.mantis?.length ? (
              <Space size={[8, 8]} wrap>
                {record.mantis.map((issue) => (
                  <a key={issue.value} href={issue.url} target="_blank" rel="noreferrer">
                    #{issue.value}
                  </a>
                ))}
              </Space>
            ) : (
              <Text type="secondary">None provided</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Share Link">
            <a href={shareLink}>{shareLink}</a>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
};

export default AcceptableTestDetail;

