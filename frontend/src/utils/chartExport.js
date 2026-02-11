import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

/**
 * Export chart as PNG image
 * @param {Object} echartsInstance - ECharts instance
 * @param {string} filename - Filename for the exported image
 * @returns {string} - Data URL of the exported image
 */
export const exportChartAsPNG = (echartsInstance, filename) => {
  if (!echartsInstance) {
    throw new Error('ECharts instance is required');
  }

  const dataURL = echartsInstance.getDataURL({
    type: 'png',
    pixelRatio: 2, // High resolution for better quality
    backgroundColor: '#fff'
  });

  // Create download link
  const link = document.createElement('a');
  link.download = filename || `chart-${new Date().getTime()}.png`;
  link.href = dataURL;
  link.click();

  return dataURL;
};

/**
 * Export chart as PDF document
 * @param {Object} echartsInstance - ECharts instance
 * @param {string} title - Chart title for the PDF
 * @param {string} filename - Filename for the exported PDF
 */
export const exportChartAsPDF = (echartsInstance, title, filename) => {
  if (!echartsInstance) {
    throw new Error('ECharts instance is required');
  }

  // Get chart image as data URL
  const dataURL = echartsInstance.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff'
  });

  // Create PDF
  const pdf = new jsPDF({
    orientation: 'landscape',
    unit: 'px',
    format: [800, 600]
  });

  // Add title
  pdf.setFontSize(18);
  pdf.text(title || 'Chart Export', 20, 30);

  // Add timestamp
  pdf.setFontSize(12);
  pdf.text(`Exported on: ${new Date().toLocaleString()}`, 20, 50);

  // Add chart image
  const imgProps = pdf.getImageProperties(dataURL);
  const pdfWidth = pdf.internal.pageSize.getWidth();
  const pdfHeight = pdf.internal.pageSize.getHeight();
  const imgWidth = pdfWidth - 40;
  const imgHeight = (imgProps.height * imgWidth) / imgProps.width;
  const xOffset = 20;
  const yOffset = 70;

  pdf.addImage(dataURL, 'PNG', xOffset, yOffset, imgWidth, imgHeight);

  // Save PDF
  pdf.save(filename || `chart-${new Date().getTime()}.pdf`);
};

/**
 * Export full dashboard page as PDF document
 * @param {Object} element - DOM element to capture
 * @param {string} filename - Filename for the exported PDF
 */
export const exportFullPageAsPDF = async (element, filename) => {
  if (!element) {
    throw new Error('DOM element is required');
  }

  try {
    // Capture the element as canvas
    const canvas = await html2canvas(element, {
      scale: 2, // Higher resolution for better quality
      useCORS: true,
      backgroundColor: '#ffffff'
    });

    // Convert canvas to image data
    const imgData = canvas.toDataURL('image/png');

    // Create PDF
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'px',
      format: [canvas.width, canvas.height]
    });

    // Add title
    pdf.setFontSize(18);
    pdf.text('Analytics Dashboard Export', 20, 30);

    // Add timestamp
    pdf.setFontSize(12);
    pdf.text(`Exported on: ${new Date().toLocaleString()}`, 20, 50);

    // Add captured image
    const imgWidth = pdf.internal.pageSize.getWidth();
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    pdf.addImage(imgData, 'PNG', 0, 70, imgWidth, imgHeight);

    // Save PDF
    pdf.save(filename || `analytics-dashboard-${new Date().getTime()}.pdf`);
  } catch (error) {
    console.error('Export error:', error);
    throw new Error('Failed to export dashboard');
  }
};

/**
 * Generate filename based on chart title and current date
 * @param {string} chartTitle - Title of the chart
 * @param {string} extension - File extension (png, pdf)
 * @returns {string} - Generated filename
 */
export const generateFilename = (chartTitle, extension) => {
  const date = new Date();
  const dateString = date.toISOString().split('T')[0];
  const timeString = date.toTimeString().split(' ')[0].replace(/:/g, '-');
  const cleanTitle = chartTitle.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();

  return `${cleanTitle}-${dateString}-${timeString}.${extension}`;
};

export default {
  exportChartAsPNG,
  exportChartAsPDF,
  exportFullPageAsPDF,
  generateFilename
};