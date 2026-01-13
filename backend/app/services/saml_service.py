"""SAML Authentication Service"""
import logging
import os
from typing import Optional, Dict, Any
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from app.core.config import settings

logger = logging.getLogger(__name__)


class SAMLService:
    """SAML authentication service using python3-saml"""

    def __init__(self):
        """Initialize SAML service with configuration"""
        self.settings = self._load_saml_settings()

    def _load_saml_settings(self) -> Dict[str, Any]:
        """
        Load SAML settings from environment variables or config

        Returns:
            SAML settings dictionary
        """
        # Base URL for the application
        base_url = os.getenv("SAML_SP_BASE_URL", "http://localhost:8000")

        # SAML settings
        saml_settings = {
            "strict": True,
            "debug": os.getenv("SAML_DEBUG", "False").lower() == "true",
            "sp": {
                "entityId": os.getenv("SAML_SP_ENTITY_ID", f"{base_url}/api/saml/metadata"),
                "assertionConsumerService": {
                    "url": f"{base_url}/api/saml/acs",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": f"{base_url}/api/saml/sls",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": os.getenv("SAML_SP_CERT", ""),
                "privateKey": os.getenv("SAML_SP_PRIVATE_KEY", "")
            },
            "idp": {
                "entityId": os.getenv("SAML_IDP_ENTITY_ID", ""),
                "singleSignOnService": {
                    "url": os.getenv("SAML_IDP_SSO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": os.getenv("SAML_IDP_SLO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": os.getenv("SAML_IDP_CERT", "")
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": False,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True
            }
        }

        return saml_settings

    def prepare_flask_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare request data in the format expected by python3-saml

        Args:
            request_data: FastAPI request data

        Returns:
            Request data in python3-saml format
        """
        return {
            'https': 'on' if request_data.get('scheme') == 'https' else 'off',
            'http_host': request_data.get('http_host', 'localhost:8000'),
            'server_port': request_data.get('server_port', 8000),
            'script_name': request_data.get('script_name', ''),
            'get_data': request_data.get('get_data', {}),
            'post_data': request_data.get('post_data', {})
        }

    def create_auth_object(self, request_data: Dict[str, Any]) -> OneLogin_Saml2_Auth:
        """
        Create SAML auth object

        Args:
            request_data: Request data in python3-saml format

        Returns:
            SAML auth object
        """
        return OneLogin_Saml2_Auth(request_data, self.settings)

    def get_login_url(self, relay_state: Optional[str] = None) -> str:
        """
        Get SAML SSO login URL

        Args:
            relay_state: Optional relay state (return URL)

        Returns:
            SAML login URL
        """
        try:
            # Create minimal request data for login
            request_data = {
                'https': 'on' if os.getenv("SAML_USE_HTTPS", "False").lower() == "true" else 'off',
                'http_host': os.getenv("SAML_SP_BASE_URL", "localhost:8000").replace("http://", "").replace("https://", ""),
                'script_name': '',
                'get_data': {},
                'post_data': {}
            }

            auth = self.create_auth_object(request_data)
            return auth.login(return_to=relay_state)

        except Exception as e:
            logger.error(f"Error generating SAML login URL: {e}")
            raise

    def process_saml_response(
        self,
        saml_response: str,
        request_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process SAML response from IdP

        Args:
            saml_response: SAML response string
            request_data: Request data

        Returns:
            User attributes dict or None if invalid
        """
        try:
            # Add SAML response to post data
            request_data['post_data'] = {'SAMLResponse': saml_response}

            auth = self.create_auth_object(request_data)
            auth.process_response()

            errors = auth.get_errors()
            if errors:
                logger.error(f"SAML response errors: {errors}")
                logger.error(f"Error reason: {auth.get_last_error_reason()}")
                return None

            if not auth.is_authenticated():
                logger.warning("SAML authentication failed")
                return None

            # Get user attributes
            attributes = auth.get_attributes()
            name_id = auth.get_nameid()
            session_index = auth.get_session_index()

            user_data = {
                'name_id': name_id,
                'session_index': session_index,
                'attributes': attributes,
                'email': attributes.get('email', [None])[0] if 'email' in attributes else None,
                'username': attributes.get('username', [None])[0] if 'username' in attributes else None,
                'full_name': attributes.get('displayName', [None])[0] if 'displayName' in attributes else None
            }

            logger.info(f"SAML authentication successful for: {name_id}")
            return user_data

        except Exception as e:
            logger.error(f"Error processing SAML response: {e}")
            return None

    def get_logout_url(
        self,
        name_id: str,
        session_index: Optional[str] = None,
        relay_state: Optional[str] = None
    ) -> str:
        """
        Get SAML SLO (Single Logout) URL

        Args:
            name_id: SAML NameID
            session_index: SAML session index
            relay_state: Optional relay state

        Returns:
            SAML logout URL
        """
        try:
            request_data = {
                'https': 'on' if os.getenv("SAML_USE_HTTPS", "False").lower() == "true" else 'off',
                'http_host': os.getenv("SAML_SP_BASE_URL", "localhost:8000").replace("http://", "").replace("https://", ""),
                'script_name': '',
                'get_data': {},
                'post_data': {}
            }

            auth = self.create_auth_object(request_data)
            return auth.logout(
                return_to=relay_state,
                name_id=name_id,
                session_index=session_index
            )

        except Exception as e:
            logger.error(f"Error generating SAML logout URL: {e}")
            raise

    def get_metadata(self) -> str:
        """
        Get SAML SP metadata XML

        Returns:
            SAML metadata XML string
        """
        try:
            saml_settings_obj = OneLogin_Saml2_Settings(self.settings)
            metadata = saml_settings_obj.get_sp_metadata()
            errors = saml_settings_obj.validate_metadata(metadata)

            if errors:
                logger.error(f"SAML metadata validation errors: {errors}")
                raise Exception(f"Invalid SAML metadata: {errors}")

            return metadata

        except Exception as e:
            logger.error(f"Error generating SAML metadata: {e}")
            raise


# Global SAML service instance
saml_service = SAMLService()
