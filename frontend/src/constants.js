export const API_URL = import.meta.env.VITE_API_URL || '';
// Use backend proxy to avoid mixed content errors
export const DEVICE_NODES_API_BASE_URL = `${API_URL}/api/device/nodes/proxy`;
