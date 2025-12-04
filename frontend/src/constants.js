const getApiUrl = () => {
  const raw = import.meta.env.VITE_API_URL || 'https://mtp.qa.fortinet-us.com';

  if (!raw) return '';

  try {
    const { origin } = typeof window !== 'undefined' ? window.location : { origin: undefined, protocol: undefined };
    const url = new URL(raw, origin);

    // Align protocol with the current page to avoid mixed content errors when served over HTTPS.
    if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
      url.protocol = 'https:';
    }

    return url.toString().replace(/\/$/, '');
  } catch (error) {
    // Fall back to the raw value if URL parsing fails.
    const sanitized = raw.replace(/\/$/, '');

    // If we're on HTTPS, force HTTPS even when parsing failed.
    if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
      return sanitized.replace(/^http:\/\//i, 'https://');
    }

    return sanitized;
  }
};

export const API_URL = getApiUrl();
console.log(API_URL)
// Use backend proxy to avoid mixed content errors
export const DEVICE_NODES_API_BASE_URL = `${API_URL}/api/device/nodes/proxy`;

const getJenkinsCloudApiUrl = () => {
  const raw = import.meta.env.VITE_JENKINS_CLOUD_API_URL ||
    'http://10.160.24.88:31224/api/v1/jenkins_cloud';

  const hasExplicitProtocol = /^https?:\/\//i.test(raw);

  if (!raw) return '';

  try {
    const { origin } = typeof window !== 'undefined' ? window.location : { origin: undefined, protocol: undefined };
    const url = new URL(raw, origin);

    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && !hasExplicitProtocol) {
      url.protocol = 'https:';
    }

    return url.toString().replace(/\/$/, '');
  } catch (error) {
    const sanitized = raw.replace(/\/$/, '');

    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && !hasExplicitProtocol) {
      return sanitized.replace(/^http:\/\//i, 'https://');
    }

    return sanitized;
  }
};

export const JENKINS_CLOUD_API_URL = getJenkinsCloudApiUrl();
