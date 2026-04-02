import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Form,
  message,
  Space,
  Tag,
  Modal,
  Typography,
  Descriptions,
} from 'antd';
import {
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';

const { Text } = Typography;
const { Option } = Select;

const JenkinsJobStatus = () => {
  const [jobStatuses, setJobStatuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedJob, setSelectedJob] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [queryForm] = Form.useForm();

  // Status color mapping
  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return 'blue';
      case 'completed':
        return 'green';
      case 'pending':
        return 'orange';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <SyncOutlined spin />;
      case 'completed':
        return <CheckCircleOutlined />;
      case 'pending':
        return <ClockCircleOutlined />;
      default:
        return null;
    }
  };

  const getStatusDescription = (status) => {
    switch (status) {
      case 'running':
        return '当前有正在运行的构建';
      case 'completed':
        return '最近一次构建已完成';
      case 'pending':
        return '构建尚未开始';
      default:
        return '未知状态';
    }
  };

  // Fetch job statuses
  const fetchJobStatuses = async (filter = null) => {
    setLoading(true);
    try {
      const params = {};
      if (filter && filter !== 'all') {
        params.status = filter;
      }

      const response = await axios.get(`${API_URL}/api/jenkins-job-status/list`, { params });
      setJobStatuses(response.data || []);
    } catch (error) {
      console.error('Failed to fetch job statuses:', error);
      message.error('Failed to fetch job statuses');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobStatuses(statusFilter);
  }, [statusFilter]);

  // Handle query job status
  const handleQueryJob = async (values) => {
    const { job_url, timestamp } = values;

    if (!job_url) {
      message.error('Please enter a Job URL');
      return;
    }

    try {
      const params = { job_url };
      if (timestamp) {
        params.timestamp = timestamp;
      }

      const response = await axios.get(`${API_URL}/api/jenkins-job-status/status`, { params });
      setSelectedJob(response.data);
      setModalVisible(true);
    } catch (error) {
      if (error.response?.status === 404) {
        message.info('Job status not found. You can update to fetch from Jenkins.');
        // Try to update from Jenkins
        handleUpdateJob({ job_url, timestamp });
      } else {
        message.error('Failed to query job status');
      }
    }
  };

  // Handle update job status
  const handleUpdateJob = async (values) => {
    const { job_url, job_name, timestamp } = values;

    if (!job_url) {
      message.error('Please enter a Job URL');
      return;
    }

    setLoading(true);
    try {
      const params = { job_url };
      if (job_name) {
        params.job_name = job_name;
      }
      if (timestamp) {
        params.timestamp = timestamp;
      }

      const response = await axios.post(`${API_URL}/api/jenkins-job-status/update`, null, { params });
      setSelectedJob(response.data);
      setModalVisible(true);
      fetchJobStatuses(statusFilter);
      message.success('Job status updated from Jenkins');
    } catch (error) {
      console.error('Failed to update job status:', error);
      message.error(`Failed to update job status: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle refresh all
  const handleRefreshAll = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/jenkins-job-status/refresh-all`);
      message.success(response.data.message);
      fetchJobStatuses(statusFilter);
    } catch (error) {
      console.error('Failed to refresh all:', error);
      message.error('Failed to refresh all job statuses');
    }
  };

  // Handle delete job status
  const handleDelete = async (jobUrl) => {
    Modal.confirm({
      title: 'Are you sure to delete this job status?',
      content: 'This action cannot be undone.',
      onOk: async () => {
        try {
          await axios.delete(`${API_URL}/api/jenkins-job-status/delete`, {
            params: { job_url: jobUrl },
          });
          message.success('Job status deleted');
          fetchJobStatuses(statusFilter);
        } catch (error) {
          message.error('Failed to delete job status');
        }
      },
    });
  };

  // Table columns
  const columns = [
    {
      title: 'Job Name',
      dataIndex: 'job_name',
      key: 'job_name',
      render: (text, record) => (
        <Space>
          {getStatusIcon(record.computed_status)}
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: 'Job URL',
      dataIndex: 'job_url',
      key: 'job_url',
      render: (text) => (
        <a href={text} target="_blank" rel="noopener noreferrer">
          {text}
        </a>
      ),
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'computed_status',
      key: 'computed_status',
      render: (status) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status?.toUpperCase()}
        </Tag>
      ),
      filters: [
        { text: 'All', value: 'all' },
        { text: 'Running', value: 'running' },
        { text: 'Completed', value: 'completed' },
        { text: 'Pending', value: 'pending' },
      ],
      onFilter: (value, record) => value === 'all' || record.computed_status === value,
    },
    {
      title: 'Status Description',
      dataIndex: 'computed_status',
      key: 'status_description',
      render: (status) => getStatusDescription(status),
    },
    {
      title: 'Running Build',
      dataIndex: 'running_build_number',
      key: 'running_build_number',
      render: (num) => num ? `#${num}` : '-',
    },
    {
      title: 'Last Completed Build',
      key: 'last_completed',
      render: (_, record) => {
        if (record.last_completed_build_number) {
          return `#${record.last_completed_build_number} (${record.last_completed_build_result || 'UNKNOWN'})`;
        }
        return '-';
      },
    },
    {
      title: 'Parameter Timestamp',
      dataIndex: 'parameter_timestamp',
      key: 'parameter_timestamp',
      render: (ts) => ts ? new Date(ts).toLocaleString() : '-',
    },
    {
      title: 'Last Checked',
      dataIndex: 'last_checked_at',
      key: 'last_checked_at',
      render: (ts) => ts ? new Date(ts).toLocaleString() : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setSelectedJob(record);
              setModalVisible(true);
            }}
          >
            View
          </Button>
          <Button
            size="small"
            danger
            onClick={() => handleDelete(record.job_url)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="Jenkins Job Status Monitor"
        extra={
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Option value="all">All</Option>
              <Option value="running">Running</Option>
              <Option value="completed">Completed</Option>
              <Option value="pending">Pending</Option>
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchJobStatuses(statusFilter)}
            >
              Refresh
            </Button>
            <Button
              icon={<SyncOutlined />}
              onClick={handleRefreshAll}
              loading={loading}
            >
              Refresh All
            </Button>
          </Space>
        }
      >
        {/* Query Form */}
        <Form
          form={queryForm}
          layout="inline"
          onFinish={handleQueryJob}
          style={{ marginBottom: 16 }}
        >
          <Form.Item
            name="job_url"
            label="Jenkins Job URL"
            rules={[{ required: false }]}
            style={{ minWidth: 300 }}
          >
            <Input placeholder="http://jenkins/job/.../" />
          </Form.Item>
          <Form.Item
            name="timestamp"
            label="Reference Timestamp"
            rules={[{ required: false }]}
          >
            <Input type="datetime-local" placeholder="ISO format timestamp" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                Query
              </Button>
              <Button
                htmlType="submit"
                onClick={() => queryForm.setFieldsValue({ job_url: '', timestamp: '' })}
              >
                Reset
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* Job Status Table */}
        <Table
          columns={columns}
          dataSource={jobStatuses}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 'max-content' }}
        />
      </Card>

      {/* Job Status Detail Modal */}
      <Modal
        title={
          <Space>
            {selectedJob?.computed_status && getStatusIcon(selectedJob.computed_status)}
            Job Status Details
          </Space>
        }
        visible={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setSelectedJob(null);
        }}
        footer={[
          <Button
            key="close"
            onClick={() => {
              setModalVisible(false);
              setSelectedJob(null);
            }}
          >
            Close
          </Button>,
          <Button
            key="refresh"
            icon={<SyncOutlined />}
            onClick={() => {
              if (selectedJob?.job_url) {
                handleUpdateJob({
                  job_url: selectedJob.job_url,
                  job_name: selectedJob.job_name,
                  timestamp: selectedJob.parameter_timestamp
                    ? new Date(selectedJob.parameter_timestamp).toISOString()
                    : undefined,
                });
              }
            }}
          >
            Refresh from Jenkins
          </Button>,
        ]}
        width={800}
      >
        {selectedJob && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Job Name">{selectedJob.job_name}</Descriptions.Item>
            <Descriptions.Item label="Job URL">
              <a href={selectedJob.job_url} target="_blank" rel="noopener noreferrer">
                {selectedJob.job_url}
              </a>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={getStatusColor(selectedJob.computed_status)}>
                {getStatusIcon(selectedJob.computed_status)}
                {selectedJob.computed_status?.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status Description">
              {getStatusDescription(selectedJob.computed_status)}
            </Descriptions.Item>
            <Descriptions.Item label="Running Build">
              {selectedJob.running_build_number ? `#${selectedJob.running_build_number}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Running Build ETA">
              {selectedJob.running_build_eta ? `${selectedJob.running_build_eta}ms` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Last Completed Build">
              {selectedJob.last_completed_build_number
                ? `#${selectedJob.last_completed_build_number} (${selectedJob.last_completed_build_result || 'UNKNOWN'})`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Parameter Timestamp">
              {selectedJob.parameter_timestamp
                ? new Date(selectedJob.parameter_timestamp).toLocaleString()
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Last Checked">
              {selectedJob.last_checked_at
                ? new Date(selectedJob.last_checked_at).toLocaleString()
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Status Computed At">
              {selectedJob.status_computed_at
                ? new Date(selectedJob.status_computed_at).toLocaleString()
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default JenkinsJobStatus;
