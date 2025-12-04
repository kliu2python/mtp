const getApiUrl = () => {
  const raw = import.meta.env.VITE_API_URL || '';

  if (!raw) return '';

  try {
    const url = new URL(raw, typeof window !== 'undefined' ? window.location.origin : undefined);

    // Align protocol with the current page to avoid mixed content errors when served over HTTPS.
    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && url.protocol === 'http:') {
      url.protocol = 'https:';
    }

    return url.toString().replace(/\/$/, '');
  } catch (error) {
    // Fall back to the raw value if URL parsing fails.
    return raw.replace(/\/$/, '');
  }
};

export const API_URL = getApiUrl();
// Use backend proxy to avoid mixed content errors
export const DEVICE_NODES_API_BASE_URL = `${API_URL}/api/device/nodes/proxy`;
