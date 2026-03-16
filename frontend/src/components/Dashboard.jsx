import React, { useEffect, useRef, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Divider,
  Dropdown,
  Row,
  Select,
  Space,
  Statistic,
  Tabs,
  Tag,
  Typography,
  message
} from 'antd';
import {
  BugOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  DownloadOutlined,
  MobileOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';
import { API_URL } from '../constants';
import { PassRateBarChart, TestCaseDistributionPieChart, PlatformComparisonBarChart } from './TestCharts';
import { exportChartAsPDF, exportChartAsPNG, exportFullPageAsPDF, generateFilename } from '../utils/chartExport';

const { Text } = Typography;

const Dashboard = () => {
  const [stats, setStats] = useState({});
  const [releaseTests, setReleaseTests] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filter states
  const [versionFilter, setVersionFilter] = useState(null);
  const [platformFilter, setPlatformFilter] = useState(null);
  const [projectFilter, setProjectFilter] = useState(null);

  // Refs for chart components
  const passRateChartRef = useRef(null);
  const testCaseDistributionChartRef = useRef(null);
  const platformComparisonChartRef = useRef(null);

  // Ref for Analytics tab content
  const analyticsTabRef = useRef(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    const [vmsRes, devicesRes, mantisRes, releaseTestsRes] = await Promise.allSettled([
      axios.get(`${API_URL}/api/vms/stats/summary`),
      axios.get(`${API_URL}/api/devices/stats/summary`),
      axios.get(`${API_URL}/api/mantis/`, { params: { page: 1, page_size: 1 } }),
      axios.get(`${API_URL}/api/release-tests`)
    ]);

    const nextStats = {};

    if (vmsRes.status === 'fulfilled') {
      nextStats.vms = vmsRes.value.data;
    } else {
      message.error('Failed to fetch VM statistics');
    }

    if (devicesRes.status === 'fulfilled') {
      nextStats.devices = devicesRes.value.data;
    } else {
      message.error('Failed to fetch device statistics');
    }

    if (mantisRes.status === 'fulfilled') {
      nextStats.mantis = mantisRes.value.data;
    }

    if (releaseTestsRes.status === 'fulfilled') {
      setReleaseTests(releaseTestsRes.value.data);
    } else {
      message.error('Failed to fetch release test data');
    }

    setStats(nextStats);
    setLoading(false);
  };

  if (loading) return <div>Loading...</div>;

  // Transform release test data for pass rate chart
  const getPassRateData = () => {
    const cycleMap = {};
    const filteredTests = getFilteredReleaseTests();

    filteredTests.forEach(test => {
      const platform = test.platform || 'Unknown';
      const version = test.version || 'Unknown';
      const key = `${platform}-${version}`;

      if (!cycleMap[key]) {
        cycleMap[key] = {
          key: key,
          platform: platform,
          version: version,
          totalBuilds: 0,
          passedBuilds: 0,
          totalTests: 0,
          passedTests: 0,
          failedTests: 0,
          skippedTests: 0,
          tests: [],
          uniqueBuilds: new Set(),
          passedBuildsSet: new Set()
        };
      }

      const cycleData = cycleMap[key];

      // Only count each unique build once
      const buildIdentifier = test.build_number || `unknown-${Date.now()}-${Math.random()}`;
      if (!cycleData.uniqueBuilds.has(buildIdentifier)) {
        cycleData.uniqueBuilds.add(buildIdentifier);
        cycleData.totalBuilds++;

        // Track passed builds separately to ensure uniqueness
        if (test.status === 'passed') {
          cycleData.passedBuildsSet.add(buildIdentifier);
        }
      } else {
        // For duplicate builds, still check if this one is passed (might be a more recent run)
        if (test.status === 'passed') {
          cycleData.passedBuildsSet.add(buildIdentifier);
        }
      }

      cycleData.tests.push(test);

      // Calculate counts based on actual test cases if available
      if (test.test_cases && Array.isArray(test.test_cases)) {
        const passedCount = test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'PASSED';
        }).length;

        const failedCount = test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'FAILED' || status === 'BROKEN';
        }).length;

        const skippedCount = test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'SKIPPED';
        }).length;

        cycleData.totalTests += passedCount + failedCount + skippedCount;
        cycleData.passedTests += passedCount;
        cycleData.failedTests += failedCount;
        cycleData.skippedTests += skippedCount;
      } else {
        // Fallback to original counter fields if test cases aren't available
        cycleData.totalTests += (test.passed_count || 0) + (test.failed_count || 0) + (test.skipped_count || 0);
        cycleData.passedTests += test.passed_count || 0;
        cycleData.failedTests += test.failed_count || 0;
        cycleData.skippedTests += test.skipped_count || 0;
      }
    });

    // Convert to array format and calculate pass rates
    const cycleArray = Object.values(cycleMap).map(cycleData => {
      // Set the actual passed builds count from our unique set
      cycleData.passedBuilds = cycleData.passedBuildsSet.size;

      const buildPassRate = cycleData.totalBuilds > 0
        ? Math.round((cycleData.passedBuilds / cycleData.totalBuilds) * 100)
        : 0;

      const testPassRate = cycleData.totalTests > 0
        ? Math.round((cycleData.passedTests / cycleData.totalTests) * 100)
        : 0;

      return {
        ...cycleData,
        buildPassRate,
        testPassRate
      };
    });

    // Sort by test pass rate and take top 10
    return cycleArray
      .sort((a, b) => b.testPassRate - a.testPassRate)
      .slice(0, 10)
      .map(cycle => ({
        label: `${cycle.platform} ${cycle.version}`,
        value: cycle.testPassRate,
        failedPercentage: cycle.totalTests > 0
          ? Math.round((cycle.failedTests / cycle.totalTests) * 100)
          : 0
      }));
  };

  // Transform release test data for test case distribution chart
  const getTestCaseDistributionData = () => {
    let totalPassed = 0;
    let totalFailed = 0;
    let totalSkipped = 0;

    const filteredTests = getFilteredReleaseTests();

    filteredTests.forEach(test => {
      // Calculate counts based on actual test cases if available
      if (test.test_cases && Array.isArray(test.test_cases)) {
        totalPassed += test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'PASSED';
        }).length;

        totalFailed += test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'FAILED' || status === 'BROKEN';
        }).length;

        totalSkipped += test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'SKIPPED';
        }).length;
      } else {
        // Fallback to original counter fields if test cases aren't available
        totalPassed += test.passed_count || 0;
        totalFailed += test.failed_count || 0;
        totalSkipped += test.skipped_count || 0;
      }
    });

    return [
      { value: totalPassed, name: 'Passed', itemStyle: { color: '#52c41a' } },
      { value: totalFailed, name: 'Failed', itemStyle: { color: '#ff4d4f' } },
      { value: totalSkipped, name: 'Skipped', itemStyle: { color: '#faad14' } }
    ];
  };

  // Transform release test data for platform comparison chart
  const getPlatformComparisonData = () => {
    const platformMap = {};
    const filteredTests = getFilteredReleaseTests();

    filteredTests.forEach(test => {
      const platform = test.platform || 'Unknown';

      if (!platformMap[platform]) {
        platformMap[platform] = {
          platform: platform,
          passed: 0,
          failed: 0,
          total: 0
        };
      }

      const platformData = platformMap[platform];

      // Calculate counts based on actual test cases if available
      if (test.test_cases && Array.isArray(test.test_cases)) {
        const passedCount = test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'PASSED';
        }).length;

        const failedCount = test.test_cases.filter(tc => {
          const status = tc.status ? tc.status.toString().toUpperCase() : '';
          return status === 'FAILED' || status === 'BROKEN';
        }).length;

        platformData.passed += passedCount;
        platformData.failed += failedCount;
        platformData.total += passedCount + failedCount;
      } else {
        // Fallback to original counter fields if test cases aren't available
        platformData.passed += test.passed_count || 0;
        platformData.failed += test.failed_count || 0;
        platformData.total += (test.passed_count || 0) + (test.failed_count || 0);
      }
    });

    return Object.values(platformMap);
  };

  const totalVms = stats?.vms?.vms?.total || 0;
  const runningVms = stats?.vms?.vms?.running || 0;
  const testingVms = stats?.vms?.vms?.testing || 0;
  const availableTestbeds = Math.max(totalVms - testingVms, 0);
  const stoppedVms = Math.max(totalVms - runningVms - testingVms, 0);

  const totalDevices = stats?.devices?.total || 0;
  const availableDevices = stats?.devices?.by_status?.available || 0;
  const busyDevices = stats?.devices?.by_status?.busy || 0;

  const tests24h = stats?.vms?.tests_24h;
  const mantisTotal = stats?.mantis?.total || 0;
  const mantisOpen = stats?.mantis?.status_counts?.open || stats?.mantis?.status_counts?.opened || 0;
  const mantisResolved = stats?.mantis?.status_counts?.resolved || 0;
  const mantisClosed = stats?.mantis?.status_counts?.closed || 0;

  // Extract unique values for filter options
  const getUniqueVersions = () => {
    const versions = releaseTests.map(test => test.version).filter(Boolean);
    return [...new Set(versions)].sort();
  };

  const getUniquePlatforms = () => {
    const platforms = releaseTests.map(test => test.platform).filter(Boolean);
    return [...new Set(platforms)].sort();
  };

  const getUniqueProjects = () => {
    const projects = releaseTests.map(test => test.project).filter(Boolean);
    return [...new Set(projects)].sort();
  };

  // Filter release tests based on active filters
  const getFilteredReleaseTests = () => {
    return releaseTests.filter(test => {
      if (versionFilter && test.version !== versionFilter) {
        return false;
      }
      if (platformFilter && test.platform !== platformFilter) {
        return false;
      }
      if (projectFilter && test.project !== projectFilter) {
        return false;
      }
      return true;
    });
  };

  // Reset all filters
  const resetFilters = () => {
    setVersionFilter(null);
    setPlatformFilter(null);
    setProjectFilter(null);
  };

  // Chart export handlers
  const handleExportChart = (chartRef, chartTitle, format) => {
    try {
      if (!chartRef.current) {
        message.error('Chart is not available for export');
        return;
      }

      const echartsInstance = chartRef.current.getEchartsInstance();

      if (format === 'png') {
        const filename = generateFilename(chartTitle, 'png');
        exportChartAsPNG(echartsInstance, filename);
      } else if (format === 'pdf') {
        const filename = generateFilename(chartTitle, 'pdf');
        exportChartAsPDF(echartsInstance, chartTitle, filename);
      }
    } catch (error) {
      console.error('Export error:', error);
      message.error('Failed to export chart');
    }
  };

  // Full page export handler
  const handleExportFullPage = async () => {
    try {
      if (!analyticsTabRef.current) {
        message.error('Analytics content is not available for export');
        return;
      }

      const filename = generateFilename('analytics-dashboard', 'pdf');
      await exportFullPageAsPDF(analyticsTabRef.current, filename);
      message.success('Analytics dashboard exported successfully');
    } catch (error) {
      console.error('Full page export error:', error);
      message.error('Failed to export analytics dashboard');
    }
  };

  // Create export dropdown menus
  const createExportMenu = (chartRef, chartTitle) => [
    {
      key: 'png',
      label: 'Export as PNG',
      onClick: () => handleExportChart(chartRef, chartTitle, 'png')
    },
    {
      key: 'pdf',
      label: 'Export as PDF',
      onClick: () => handleExportChart(chartRef, chartTitle, 'pdf')
    }
  ];

  // Tab items configuration
  const tabItems = [
    {
      key: 'overview',
      label: 'Overview',
      children: (
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic
                title="Available Testbeds"
                value={availableTestbeds}
                prefix={<CloudServerOutlined />}
              />
              <Text type="secondary">{runningVms} running / {testingVms} testing</Text>
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Running Tests"
                value={testingVms}
                prefix={<PlayCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
              <Text type="secondary">Linked to active testbeds</Text>
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Lab Devices Available"
                value={availableDevices}
                prefix={<MobileOutlined />}
              />
              <Text type="secondary">{busyDevices} busy / {totalDevices} total</Text>
            </Card>
          </Col>
          <Col span={12} style={{ marginTop: 24 }}>
            <Card title="Test Activity (last 24h)" extra={<Tag color="blue">{tests24h?.total || 0} runs</Tag>}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="Pass Rate"
                    value={tests24h?.pass_rate || 0}
                    suffix="%"
                    valueStyle={{ color: (tests24h?.pass_rate || 0) > 80 ? '#3f8600' : '#cf1322' }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic title="Passed" value={tests24h?.passed || 0} prefix={<CheckCircleOutlined />} />
                </Col>
                <Col span={8}>
                  <Statistic title="Failed" value={tests24h?.failed || 0} prefix={<BugOutlined />} />
                </Col>
              </Row>
            </Card>
          </Col>
          <Col span={12} style={{ marginTop: 24 }}>
            <Card title="Mantis Overview" extra={<Tag color="purple">{mantisTotal} issues</Tag>}>
              <Space size={16} wrap>
                <Statistic title="Open" value={mantisOpen} prefix={<BugOutlined />} />
                <Statistic title="Resolved" value={mantisResolved} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
                <Statistic title="Closed" value={mantisClosed} prefix={<PlayCircleOutlined />} />
              </Space>
              {stats?.mantis?.last_updated && (
                <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                  Last sync: {new Date(stats.mantis.last_updated).toLocaleString()}
                </Text>
              )}
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'infrastructure',
      label: 'Infrastructure',
      children: (
        <>
          <Row gutter={16}>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Available Testbeds"
                  value={availableTestbeds}
                  prefix={<CloudServerOutlined />}
                />
                <Text type="secondary">{runningVms} running / {testingVms} testing</Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Running Tests"
                  value={testingVms}
                  prefix={<PlayCircleOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
                <Text type="secondary">Linked to active testbeds</Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Lab Devices Available"
                  value={availableDevices}
                  prefix={<MobileOutlined />}
                />
                <Text type="secondary">{busyDevices} busy / {totalDevices} total</Text>
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginTop: 24 }}>
            <Col span={12}>
              <Card title="Platform Distribution">
                {stats?.vms?.vms?.by_platform && (
                  <Space direction="vertical" size={6}>
                    <Text>FortiGate: {stats.vms.vms.by_platform.FortiGate}</Text>
                    <Text>FortiAuthenticator: {stats.vms.vms.by_platform.FortiAuthenticator}</Text>
                  </Space>
                )}
                <Divider />
                <Space size={12}>
                  <Tag color="green">Running: {runningVms}</Tag>
                  <Tag color="orange">Testing: {testingVms}</Tag>
                  <Tag>Stopped: {stoppedVms}</Tag>
                </Space>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Device Distribution">
                {stats?.devices?.by_platform && (
                  <Space direction="vertical" size={6}>
                    <Text>iOS: {stats.devices.by_platform.iOS}</Text>
                    <Text>Android: {stats.devices.by_platform.Android}</Text>
                  </Space>
                )}
                <Divider />
                <Space size={12}>
                  <Tag color="green">Available: {availableDevices}</Tag>
                  <Tag color="orange">Busy: {busyDevices}</Tag>
                  <Tag color="red">Offline: {stats?.devices?.by_status?.offline || 0}</Tag>
                </Space>
              </Card>
            </Col>
          </Row>
        </>
      ),
    },
    {
      key: 'activity',
      label: 'Activity',
      children: (
        <Row gutter={16}>
          <Col span={12}>
            <Card title="Test Activity (last 24h)" extra={<Tag color="blue">{tests24h?.total || 0} runs</Tag>}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="Pass Rate"
                    value={tests24h?.pass_rate || 0}
                    suffix="%"
                    valueStyle={{ color: (tests24h?.pass_rate || 0) > 80 ? '#3f8600' : '#cf1322' }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic title="Passed" value={tests24h?.passed || 0} prefix={<CheckCircleOutlined />} />
                </Col>
                <Col span={8}>
                  <Statistic title="Failed" value={tests24h?.failed || 0} prefix={<BugOutlined />} />
                </Col>
              </Row>
            </Card>
          </Col>
          <Col span={12}>
            <Card title="Mantis Overview" extra={<Tag color="purple">{mantisTotal} issues</Tag>}>
              <Space size={16} wrap>
                <Statistic title="Open" value={mantisOpen} prefix={<BugOutlined />} />
                <Statistic title="Resolved" value={mantisResolved} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
                <Statistic title="Closed" value={mantisClosed} prefix={<PlayCircleOutlined />} />
              </Space>
              {stats?.mantis?.last_updated && (
                <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                  Last sync: {new Date(stats.mantis.last_updated).toLocaleString()}
                </Text>
              )}
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'analytics',
      label: 'Analytics',
      children: (
        <div ref={analyticsTabRef}>
          <div style={{ textAlign: 'right', marginBottom: 16 }}>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExportFullPage}
            >
              Export Analytics Page
            </Button>
          </div>

          {/* Filter Controls */}
          <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 6 }}>
            <Row gutter={16} align="middle">
              <Col>
                <Text strong>Filter by:</Text>
              </Col>
              <Col>
                <Select
                  style={{ width: 150 }}
                  placeholder="Version"
                  value={versionFilter}
                  onChange={setVersionFilter}
                  allowClear
                  onClear={() => setVersionFilter(null)}
                >
                  {getUniqueVersions().map(version => (
                    <Select.Option key={version} value={version}>
                      {version}
                    </Select.Option>
                  ))}
                </Select>
              </Col>
              <Col>
                <Select
                  style={{ width: 150 }}
                  placeholder="Platform"
                  value={platformFilter}
                  onChange={setPlatformFilter}
                  allowClear
                  onClear={() => setPlatformFilter(null)}
                >
                  {getUniquePlatforms().map(platform => (
                    <Select.Option key={platform} value={platform}>
                      {platform?.toUpperCase()}
                    </Select.Option>
                  ))}
                </Select>
              </Col>
              <Col>
                <Select
                  style={{ width: 150 }}
                  placeholder="Project"
                  value={projectFilter}
                  onChange={setProjectFilter}
                  allowClear
                  onClear={() => setProjectFilter(null)}
                >
                  <Select.Option value="ftm">FTM</Select.Option>
                  <Select.Option value="fortiexplorer">FortiExplorer GO</Select.Option>
                  <Select.Option value="fortiedr">FortiEDR Mobile</Select.Option>
                </Select>
              </Col>
              {(versionFilter || platformFilter || projectFilter) && (
                <Col>
                  <Button onClick={resetFilters}>
                    Clear Filters
                  </Button>
                </Col>
              )}
            </Row>
          </div>

          <Row gutter={16}>
            <Col span={12}>
              <Card
                title="Release Test Pass Rates"
                extra={
                  <Dropdown menu={{ items: createExportMenu(passRateChartRef, 'Release Test Pass Rates') }}>
                    <Button icon={<DownloadOutlined />} size="small">Export</Button>
                  </Dropdown>
                }
              >
                <PassRateBarChart ref={passRateChartRef} data={getPassRateData()} />
              </Card>
            </Col>
            <Col span={12}>
              <Card
                title="Test Case Distribution"
                extra={
                  <Dropdown menu={{ items: createExportMenu(testCaseDistributionChartRef, 'Test Case Distribution') }}>
                    <Button icon={<DownloadOutlined />} size="small">Export</Button>
                  </Dropdown>
                }
              >
                <TestCaseDistributionPieChart ref={testCaseDistributionChartRef} data={getTestCaseDistributionData()} />
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginTop: 24 }}>
            <Col span={12}>
              <Card
                title="Platform Comparison"
                extra={
                  <Dropdown menu={{ items: createExportMenu(platformComparisonChartRef, 'Platform Comparison') }}>
                    <Button icon={<DownloadOutlined />} size="small">Export</Button>
                  </Dropdown>
                }
              >
                <PlatformComparisonBarChart ref={platformComparisonChartRef} data={getPlatformComparisonData()} />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Release Test Summary">
                <Space direction="vertical" size={16}>
                  <Text>Total Release Tests: {releaseTests.length}</Text>
                  <Text>Unique Builds: {getPassRateData().length}</Text>
                  <Text>Total Test Cases: {getTestCaseDistributionData().reduce((sum, item) => sum + item.value, 0)}</Text>
                </Space>
              </Card>
            </Col>
          </Row>
        </div>
      ),
    },
  ];

  return (
    <div>
      <h1>Dashboard</h1>
      <Tabs items={tabItems} defaultActiveKey="overview" />
    </div>
  );
};

export default Dashboard;
