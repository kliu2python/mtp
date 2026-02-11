import React, { forwardRef } from 'react';
import ReactECharts from 'echarts-for-react';

// Pass Rate Bar Chart Component
export const PassRateBarChart = forwardRef(({ data }, ref) => {
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      boundaryGap: [0, 0.01],
      max: 100
    },
    yAxis: {
      type: 'category',
      data: data.map(item => item.label)
    },
    series: [
      {
        name: 'Pass Rate',
        type: 'bar',
        data: data.map(item => ({
          value: item.value,
          itemStyle: {
            color: item.failedPercentage > 25 ? '#ff4d4f' : (item.value >= 80 ? '#52c41a' : (item.value >= 50 ? '#faad14' : '#ff4d4f'))
          }
        })),
      }
    ]
  };

  return <ReactECharts ref={ref} option={option} style={{ height: 400 }} />;
});

PassRateBarChart.displayName = 'PassRateBarChart';

// Test Case Distribution Pie Chart Component
export const TestCaseDistributionPieChart = forwardRef(({ data }, ref) => {
  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: 'bottom'
    },
    series: [
      {
        name: 'Test Cases',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        data: data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };

  return <ReactECharts ref={ref} option={option} style={{ height: 400 }} />;
});

TestCaseDistributionPieChart.displayName = 'TestCaseDistributionPieChart';

// Platform Comparison Bar Chart Component
export const PlatformComparisonBarChart = forwardRef(({ data }, ref) => {
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['Passed', 'Failed']
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(item => item.platform)
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: 'Passed',
        type: 'bar',
        stack: 'Test Results',
        data: data.map(item => item.passed),
        itemStyle: { color: '#52c41a' }
      },
      {
        name: 'Failed',
        type: 'bar',
        stack: 'Test Results',
        data: data.map(item => item.failed),
        itemStyle: { color: '#ff4d4f' }
      }
    ]
  };

  return <ReactECharts ref={ref} option={option} style={{ height: 400 }} />;
});

PlatformComparisonBarChart.displayName = 'PlatformComparisonBarChart';

export default {
  PassRateBarChart,
  TestCaseDistributionPieChart,
  PlatformComparisonBarChart
};