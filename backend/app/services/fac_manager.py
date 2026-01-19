"""
FortiAuthenticator Manager Service
Handles testing connectivity and user creation with FortiAuthenticator devices
"""
import requests
import urllib3
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional

# Suppress SSL certificate warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FACManager:
    def __init__(self, host: str, admin_user: str, api_key: str):
        self.host = host
        self.base_url = f"https://{host}/api/v1"
        self.auth = HTTPBasicAuth(admin_user, api_key)
        self.verify_ssl = False
        self.timeout = 10

    def test_connection(self) -> Optional[str]:
        """
        Check connectivity and API key validity.
        Returns the firmware version if successful.
        """
        url = f"{self.base_url}/systeminfo/"
        try:
            response = requests.get(url, auth=self.auth, verify=self.verify_ssl, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get('firmware')
            return None
        except Exception as e:
            print(f"Error connecting to {self.host}: {e}")
            return None

    def check_available_tokens(self, token_category: str = 'ftm') -> List[str]:
        """
        Check if tokens can be retrieved and assigned.
        Filter by status 'available'. Categories: 'ftm' (mobile), 'ftk' (hard token).
        """
        url = f"{self.base_url}/fortitokens/"
        # Based on docs: filters available tokens of a specific type
        params = {
            "format": "json",
            "status": "available",
            "type": token_category
        }

        try:
            response = requests.get(url, auth=self.auth, params=params, verify=self.verify_ssl)

            if response.status_code == 200:
                tokens = response.json().get('objects', [])
                # In FAC 8.0.0, the field name is 'serial'
                return [t['serial'] for t in tokens]
            return []
        except Exception as e:
            print(f"Error checking available tokens: {e}")
            return []

    def create_user_with_ftc(self, username: str, email: str) -> Dict:
        """
        Create a local user and enable MFA using FortiToken Cloud (FTC).
        According to docs: set 'token_type' to 'ftc' and 'token_auth' to true.
        """
        url = f"{self.base_url}/localusers/"
        payload = {
            "username": username,
            "password": "fortinet",
            "email": email,
            "token_auth": True,
            "token_type": "ftc",  # Enable FortiToken Cloud specifically
            "ftm_act_method": "email",
        }

        try:
            # POST returns 201 Created on success
            response = requests.post(url, auth=self.auth, json=payload, verify=self.verify_ssl)

            if response.status_code == 201:
                result = {
                    "success": True,
                    "message": f"User '{username}' created with FTC MFA enabled."
                }
                self._check_and_delete_user(username=username)
                return result
            else:
                return {
                    "success": False,
                    "message": f"User creation failed: {response.status_code} - {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"User creation failed with exception: {str(e)}"
            }

    def create_user_with_ftm(self, username: str, email: str) -> Dict:
        """
        Create a local user and enable MFA using FortiTokens (FTM).
        """
        url = f"{self.base_url}/localusers/"
        payload = {
            "username": username,
            "password": "fortinet",
            "email": email,
            "token_auth": True,
            "token_type": "ftm",  # Enable FortiTokens specifically
            "ftm_act_method": "email",
        }

        try:
            # POST returns 201 Created on success
            response = requests.post(url, auth=self.auth, json=payload, verify=self.verify_ssl)

            if response.status_code == 201:
                result = {
                    "success": True,
                    "message": f"User '{username}' created with FTM MFA enabled."
                }
                self._check_and_delete_user(username=username)
                return result
            else:
                return {
                    "success": False,
                    "message": f"User creation failed: {response.status_code} - {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"User creation failed with exception: {str(e)}"
            }

    def assign_token_to_user(self, username: str, token_serial: str) -> bool:
        """
        Helper: Assign a specific serial number to an existing user.
        Uses PATCH method which returns 202 Accepted per documentation.
        """
        try:
            # Step 1: Find user ID by username
            search_url = f"{self.base_url}/localusers/"
            params = {"username": username, "format": "json"}
            search_res = requests.get(search_url, auth=self.auth, params=params, verify=self.verify_ssl)

            if search_res.status_code == 200 and search_res.json()['objects']:
                user_id = search_res.json()['objects'][0]['id']

                # Step 2: Patch the user with token_serial
                patch_url = f"{self.base_url}/localusers/{user_id}/"
                patch_data = {
                    "token_auth": True,
                    "token_serial": token_serial
                }
                res = requests.patch(patch_url, auth=self.auth, json=patch_data, verify=self.verify_ssl)
                return res.status_code == 202
            return False
        except Exception as e:
            print(f"Error assigning token to user: {e}")
            return False

    def _check_and_delete_user(self, username: str) -> None:
        """
        Helper: Check and delete a user after testing.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/localusers/?username={username}",
                auth=self.auth, verify=self.verify_ssl
            )
            if resp.status_code == 200:
                user_ids = resp.json().get("objects", [])
                for user in user_ids:
                    if user.get("username") == username:
                        user_id = user.get("id")
                        if user_id:
                            requests.delete(
                                f"{self.base_url}/localusers/{user_id}/",
                                auth=self.auth, verify=self.verify_ssl
                            )
        except Exception as e:
            print(f"Error deleting user: {e}")


def test_fortiauthenticator_connectivity(host: str, username: str, api_key: str) -> Dict:
    """
    Test FortiAuthenticator connectivity and return firmware version.
    """
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"

    fac = FACManager(host, username, api_key)
    version = fac.test_connection()

    if version:
        return {
            "success": True,
            "message": f"Successfully connected to FortiAuthenticator {host}",
            "firmware": version,
            "timestamp": timestamp
        }
    else:
        return {
            "success": False,
            "message": f"Failed to connect to FortiAuthenticator {host}",
            "timestamp": timestamp
        }


def test_fortiauthenticator_user_creation(host: str, username: str, api_key: str) -> Dict:
    """
    Test FortiAuthenticator user creation with both FTK and FTC.
    """
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"

    fac = FACManager(host, username, api_key)

    # Test 1: Check available tokens
    available_tokens = fac.check_available_tokens('ftk')

    # Test 2: Create user with FTK
    test_ftk_username = "mfa_test_ftk_temp"
    ftm_result = fac.create_user_with_ftm(test_ftk_username, "ftnt.taas.solutions@gmail.com")

    # Test 3: Create user with FTC
    test_ftc_username = "mfa_test_ftc_temp"
    ftc_result = fac.create_user_with_ftc(test_ftc_username, "ftnt.taas.solutions@gmail.com")

    return {
        "token_check": {
            "available_tokens": len(available_tokens),
            "tokens": available_tokens[:5]  # Limit to first 5 tokens
        },
        "ftm_user_creation": ftm_result,
        "ftc_user_creation": ftc_result,
        "timestamp": timestamp
    }