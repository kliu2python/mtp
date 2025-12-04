import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Input,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Button,
  message,
  Tooltip,
} from 'antd';
import {
  BugOutlined,
  CloseCircleOutlined,
  LinkOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const statusColors = {
  new: 'blue',
  feedback: 'cyan',
  acknowledged: 'geekblue',
  confirmed: 'purple',
  assigned: 'gold',
  resolved: 'green',
  closed: 'gray',
};

const priorityColors = {
  none: 'default',
  low: 'blue',
  normal: 'green',
  high: 'orange',
  urgent: 'red',
  immediate: 'volcano',
};

const severityColors = {
  feature: 'cyan',
  trivial: 'blue',
  text: 'purple',
  tweak: 'gold',
  minor: 'green',
  major: 'orange',
  crash: 'red',
  block: 'volcano',
};

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const DetailDrawer = ({ issue, onClose }) => (
  <Drawer
    width={720}
    title={
      <Space size={8}>
        <BugOutlined />
        <span>Mantis Issue {issue?.issue_id || issue?.id}</span>
      </Space>
    }
    onClose={onClose}
    open={!!issue}
  >
    {issue && (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Issue ID">{issue.issue_id || issue.id}</Descriptions.Item>
          <Descriptions.Item label="Category">{issue.category || '-'}</Descriptions.Item>
          <Descriptions.Item label="Status">
            <Tag color={statusColors[(issue.status || '').toLowerCase()] || 'default'}>
              {(issue.status || 'Unknown').toUpperCase()}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Priority">
            <Tag color={priorityColors[(issue.priority || '').toLowerCase()] || 'default'}>
              {(issue.priority || 'Unknown').toUpperCase()}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Severity">
            <Tag color={severityColors[(issue.severity || '').toLowerCase()] || 'default'}>
              {(issue.severity || 'Unknown').toUpperCase()}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Reporter ID">{issue.reporter_id || '-'}</Descriptions.Item>
          <Descriptions.Item label="Project ID">{issue.project_id || '-'}</Descriptions.Item>
          <Descriptions.Item label="Version">{issue.version || '-'}</Descriptions.Item>
          <Descriptions.Item label="Target Version">{issue.target_version || '-'}</Descriptions.Item>
          <Descriptions.Item label="Fixed In">{issue.fixed_in_version || '-'}</Descriptions.Item>
          <Descriptions.Item label="Date Submitted">{formatDate(issue.date_submitted)}</Descriptions.Item>
          <Descriptions.Item label="Last Updated">{formatDate(issue.last_updated)}</Descriptions.Item>
          <Descriptions.Item label="Scraped At">{formatDate(issue.scraped_at)}</Descriptions.Item>
          <Descriptions.Item label="Resolution" span={2}>{issue.resolution || '-'}</Descriptions.Item>
        </Descriptions>

        <Card title="Summary" size="small">
          <Paragraph>{issue.summary || 'No summary provided.'}</Paragraph>
        </Card>

        {issue.description && (
          <Card title="Description" size="small">
            <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{issue.description}</Paragraph>
          </Card>
        )}

        {issue.steps_to_reproduce && (
          <Card title="Steps to Reproduce" size="small">
            <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{issue.steps_to_reproduce}</Paragraph>
          </Card>
        )}

        {issue.additional_information && (
          <Card title="Additional Information" size="small">
            <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{issue.additional_information}</Paragraph>
          </Card>
        )}

        {issue.bugnotes && (
          <Card title="Bugnotes" size="small">
            <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{issue.bugnotes}</Paragraph>
          </Card>
        )}

        {issue.url && (
          <Card size="small">
            <Space>
              <LinkOutlined />
              <a href={issue.url} target="_blank" rel="noreferrer">View in Mantis</a>
            </Space>
          </Card>
        )}
      </Space>
    )}
  </Drawer>
);

const DEFAULT_REQUEST_PARAMS = {
  page: 1,
  page_size: 20,
  search: '',
  status: null,
  priority: null,
  severity: null,
  category: null,
  sort_by: 'date_submitted',
  sort_order: 'desc',
};

const Mantis = () => {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [requestParams, setRequestParams] = useState(DEFAULT_REQUEST_PARAMS);
  const [selectedIssue, setSelectedIssue] = useState(null);

  const fetchIssues = async (overrides = {}, options = { reset: false }) => {
    const baseParams = options.reset ? DEFAULT_REQUEST_PARAMS : requestParams;
    const params = { ...baseParams, ...overrides };
    setLoading(true);

    try {
      const { data } = await axios.get(`${API_URL}/api/mantis/`, {
        params,
      });

      setIssues(data.issues || []);
      setRequestParams(params);
      setPagination({
        current: data.page || params.page,
        pageSize: data.page_size || params.page_size,
        total: data.total || 0,
      });
    } catch (error) {
      message.error('Failed to load Mantis issues');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIssues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (value) => {
    fetchIssues({ search: value, page: 1 });
  };

  const handleFilterChange = (field, value) => {
    fetchIssues({ [field]: value || null, page: 1 });
  };

  const handleResetFilters = () => {
    fetchIssues(DEFAULT_REQUEST_PARAMS, { reset: true });
  };

  const handleTableChange = (nextPagination, filters, sorter) => {
    fetchIssues({
      page: nextPagination.current,
      page_size: nextPagination.pageSize,
      sort_by: sorter.field || requestParams.sort_by,
      sort_order: sorter.order === 'ascend' ? 'asc' : 'desc',
    });
  };

  const handleRefresh = () => {
    fetchIssues();
  };

  const summaryStats = useMemo(() => {
    const statusCount = issues.reduce((acc, issue) => {
      const key = (issue.status || 'unknown').toLowerCase();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    return {
      total: pagination.total,
      open: (statusCount.new || 0) + (statusCount.acknowledged || 0) + (statusCount.assigned || 0),
      resolved: (statusCount.resolved || 0) + (statusCount.closed || 0),
    };
  }, [issues, pagination.total]);

  const columns = [
    {
      title: 'Issue',
      dataIndex: 'issue_id',
      key: 'issue_id',
      sorter: true,
      render: (value, record) => (
        <Space size={6}>
          <Text strong>#{value || record.id}</Text>
          {record.url && (
            <Tooltip title="Open in Mantis">
              <a href={record.url} target="_blank" rel="noreferrer">
                <LinkOutlined />
              </a>
            </Tooltip>
          )}
        </Space>
      ),
      width: 120,
    },
    {
      title: 'Summary',
      dataIndex: 'summary',
      key: 'summary',
      sorter: true,
      ellipsis: true,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      sorter: true,
      width: 140,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      sorter: true,
      render: (value) => (
        <Tag color={statusColors[(value || '').toLowerCase()] || 'default'}>
          {(value || 'Unknown').toUpperCase()}
        </Tag>
      ),
      width: 140,
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      sorter: true,
      render: (value) => (
        <Tag color={priorityColors[(value || '').toLowerCase()] || 'default'}>
          {(value || 'Unknown').toUpperCase()}
        </Tag>
      ),
      width: 140,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      sorter: true,
      render: (value) => (
        <Tag color={severityColors[(value || '').toLowerCase()] || 'default'}>
          {(value || 'Unknown').toUpperCase()}
        </Tag>
      ),
      width: 140,
    },
    {
      title: 'Submitted',
      dataIndex: 'date_submitted',
      key: 'date_submitted',
      sorter: true,
      width: 200,
      render: (value) => formatDate(value),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Space direction="vertical" size={0}>
              <Text type="secondary">Total Issues</Text>
              <Title level={3} style={{ margin: 0 }}>{summaryStats.total}</Title>
            </Space>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Space direction="vertical" size={0}>
              <Text type="secondary">Open</Text>
              <Title level={3} style={{ margin: 0 }}>{summaryStats.open}</Title>
            </Space>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Space direction="vertical" size={0}>
              <Text type="secondary">Resolved / Closed</Text>
              <Title level={3} style={{ margin: 0 }}>{summaryStats.resolved}</Title>
            </Space>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Space direction="vertical" size={0}>
              <Text type="secondary">Current Page</Text>
              <Title level={3} style={{ margin: 0 }}>{pagination.current}</Title>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <BugOutlined />
            <span>Mantis Issues</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} disabled={loading}>
              Refresh
            </Button>
            <Button icon={<CloseCircleOutlined />} onClick={handleResetFilters} disabled={loading}>
              Reset Filters
            </Button>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Input.Search
            placeholder="Search summary, description, or category"
            allowClear
            value={requestParams.search || ''}
            onChange={(event) =>
              setRequestParams((prev) => ({
                ...prev,
                search: event.target.value,
              }))
            }
            onSearch={handleSearch}
            enterButton={<SearchOutlined />}
            style={{ width: 320 }}
          />

          <Select
            allowClear
            placeholder="Status"
            style={{ width: 160 }}
            onChange={(value) => handleFilterChange('status', value)}
            value={requestParams.status || undefined}
          >
            <Option value="new">New</Option>
            <Option value="feedback">Feedback</Option>
            <Option value="acknowledged">Acknowledged</Option>
            <Option value="confirmed">Confirmed</Option>
            <Option value="assigned">Assigned</Option>
            <Option value="resolved">Resolved</Option>
            <Option value="closed">Closed</Option>
          </Select>

          <Select
            allowClear
            placeholder="Priority"
            style={{ width: 160 }}
            onChange={(value) => handleFilterChange('priority', value)}
            value={requestParams.priority || undefined}
          >
            <Option value="none">None</Option>
            <Option value="low">Low</Option>
            <Option value="normal">Normal</Option>
            <Option value="high">High</Option>
            <Option value="urgent">Urgent</Option>
            <Option value="immediate">Immediate</Option>
          </Select>

          <Select
            allowClear
            placeholder="Severity"
            style={{ width: 160 }}
            onChange={(value) => handleFilterChange('severity', value)}
            value={requestParams.severity || undefined}
          >
            <Option value="feature">Feature</Option>
            <Option value="trivial">Trivial</Option>
            <Option value="text">Text</Option>
            <Option value="tweak">Tweak</Option>
            <Option value="minor">Minor</Option>
            <Option value="major">Major</Option>
            <Option value="crash">Crash</Option>
            <Option value="block">Block</Option>
          </Select>

          <Input
            allowClear
            placeholder="Category"
            style={{ width: 200 }}
            value={requestParams.category || ''}
            onChange={(event) => handleFilterChange('category', event.target.value || null)}
          />
        </Space>

        <Table
          rowKey={(record) => record.id}
          loading={loading}
          columns={columns}
          dataSource={issues}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100', '200'],
          }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => setSelectedIssue(record),
          })}
        />

        <Divider style={{ marginTop: 0 }} />
        <Text type="secondary">
          Click any row to view complete details, including steps to reproduce and bugnotes.
        </Text>
      </Card>

      <DetailDrawer issue={selectedIssue} onClose={() => setSelectedIssue(null)} />
    </Space>
  );
};

export default Mantis;
