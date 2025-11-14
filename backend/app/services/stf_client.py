"""
STF (Smartphone Test Farm) API Client
"""
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class STFClient:
    """Client for interacting with STF (Smartphone Test Farm) API"""

    def __init__(self, base_url: str, jwt_token: str):
        """
        Initialize STF client

        Args:
            base_url: STF server URL (e.g., "http://10.160.13.118:7100")
            jwt_token: JWT authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.jwt_token = jwt_token
        self.headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make HTTP request to STF API

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request arguments

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/api/v1{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            response.raise_for_status()

            # Some STF endpoints return empty responses
            if response.status_code == 204:
                return {'success': True}

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"STF API request failed: {e}")
            raise

    def get_user_info(self) -> Dict:
        """Get current user information"""
        return self._make_request('GET', '/user')

    def get_all_devices(self) -> List[Dict]:
        """
        Get all devices from STF

        Returns:
            List of device dictionaries
        """
        response = self._make_request('GET', '/devices')
        devices = response.get('devices', [])
        logger.info(f"Fetched {len(devices)} devices from STF")
        return devices

    def get_user_devices(self) -> List[Dict]:
        """
        Get devices currently assigned to the user

        Returns:
            List of user's devices
        """
        response = self._make_request('GET', '/user/devices')
        devices = response.get('devices', [])
        return devices

    def add_device(self, device_serial: str, timeout: int = 900000) -> Dict:
        """
        Reserve/add a device to user's pool

        Args:
            device_serial: Device serial number (UDID)
            timeout: Reservation timeout in milliseconds (default 15 min)

        Returns:
            Response dictionary
        """
        data = {'timeout': timeout}
        try:
            response = self._make_request(
                'POST',
                f'/user/devices/{device_serial}',
                json=data
            )
            logger.info(f"Device {device_serial} added to user pool")
            return response
        except Exception as e:
            logger.error(f"Failed to add device {device_serial}: {e}")
            raise

    def remove_device(self, device_serial: str) -> Dict:
        """
        Release/remove a device from user's pool

        Args:
            device_serial: Device serial number (UDID)

        Returns:
            Response dictionary
        """
        try:
            response = self._make_request(
                'DELETE',
                f'/user/devices/{device_serial}'
            )
            logger.info(f"Device {device_serial} removed from user pool")
            return response
        except Exception as e:
            logger.error(f"Failed to remove device {device_serial}: {e}")
            raise

    def get_device_info(self, device_serial: str) -> Optional[Dict]:
        """
        Get detailed information about a specific device

        Args:
            device_serial: Device serial number (UDID)

        Returns:
            Device info dictionary or None if not found
        """
        all_devices = self.get_all_devices()
        for device in all_devices:
            if device.get('serial') == device_serial:
                return device
        return None

    def remote_connect(self, device_serial: str) -> Dict:
        """
        Get remote connect URL for a device

        Args:
            device_serial: Device serial number (UDID)

        Returns:
            Remote connect information
        """
        response = self._make_request(
            'POST',
            f'/user/devices/{device_serial}/remoteConnect'
        )
        return response

    def normalize_device_data(self, stf_device: Dict) -> Dict:
        """
        Convert STF device data to MTP format

        Args:
            stf_device: STF device dictionary

        Returns:
            Normalized device data for MTP
        """
        # Determine platform
        platform = 'Android' if stf_device.get('platform') == 'Android' else 'iOS'

        # Determine device type
        device_type = 'physical_android' if platform == 'Android' else 'physical_ios'

        # Check availability
        is_present = stf_device.get('present', False)
        is_ready = stf_device.get('ready', False)
        is_using = stf_device.get('using', False)
        owner = stf_device.get('owner')

        if not is_present:
            status = 'offline'
        elif is_using or owner:
            status = 'busy'
        elif is_ready:
            status = 'available'
        else:
            status = 'offline'

        return {
            'name': stf_device.get('name', stf_device.get('model', 'Unknown')),
            'device_type': device_type,
            'platform': platform,
            'os_version': stf_device.get('version', 'Unknown'),
            'device_id': stf_device.get('serial'),
            'connection_type': 'stf',
            'status': status,
            'battery_level': stf_device.get('battery', {}).get('level', 0),
            'capabilities': {
                'manufacturer': stf_device.get('manufacturer'),
                'model': stf_device.get('model'),
                'sdk': stf_device.get('sdk'),
                'abi': stf_device.get('abi'),
                'display': stf_device.get('display'),
                'cpuPlatform': stf_device.get('cpuPlatform'),
                'network': stf_device.get('network')
            },
            'metadata': {
                'stf_serial': stf_device.get('serial'),
                'stf_present': is_present,
                'stf_ready': is_ready,
                'stf_using': is_using,
                'stf_owner': owner,
                'provider': stf_device.get('provider'),
                'remote_connect_url': stf_device.get('remoteConnectUrl')
            }
        }


# Default STF client instance
_stf_client: Optional[STFClient] = None


def get_stf_client(base_url: str = None, jwt_token: str = None) -> STFClient:
    """
    Get or create STF client instance

    Args:
        base_url: STF server URL (optional, uses default if not provided)
        jwt_token: JWT token (optional, uses default if not provided)

    Returns:
        STFClient instance
    """
    global _stf_client

    # Default configuration
    default_url = "http://10.160.13.118:7100"
    default_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiZGV2aWNlX3Byb3h5X2JvdCIsImVtYWlsIjoiYm90QGZvcnRpbmV0LmNvbSIsImlhdCI6MTc2Mjg4ODEyOSwiZXhwIjoyMDc4NDY0MTI5fQ.E4QB8OsbVl51vYjLJgscMPe2AitmLtkki7ult1jkyRg"

    url = base_url or default_url
    token = jwt_token or default_jwt

    if _stf_client is None:
        _stf_client = STFClient(url, token)

    return _stf_client
