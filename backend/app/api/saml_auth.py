"""SAML Authentication API"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.services.saml_service import saml_service
from app.services.auth_service import auth_service
from app.schemas.auth import Token
from app.api.auth import get_current_active_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/metadata")
async def saml_metadata():
    """
    Get SAML SP metadata XML

    This endpoint provides the Service Provider (SP) metadata
    that should be registered with the Identity Provider (IdP)

    Returns:
        SAML metadata XML
    """
    try:
        metadata = saml_service.get_metadata()
        return Response(content=metadata, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error generating SAML metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")


@router.get("/login")
async def saml_login(
    request: Request,
    relay_state: str = None
):
    """
    Initiate SAML SSO login

    This endpoint redirects the user to the IdP for authentication

    Args:
        request: FastAPI request object
        relay_state: Optional URL to redirect after successful login

    Returns:
        Redirect to IdP SSO URL
    """
    try:
        # Prepare request data
        request_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.headers.get('host', 'localhost:8000'),
            'server_port': request.url.port or 8000,
            'script_name': request.url.path,
            'get_data': dict(request.query_params),
            'post_data': {}
        }

        # Create SAML auth object
        auth = saml_service.create_auth_object(
            saml_service.prepare_flask_request(request_data)
        )

        # Get SSO URL
        sso_url = auth.login(return_to=relay_state)

        logger.info(f"Initiating SAML login, redirecting to: {sso_url}")
        return RedirectResponse(url=sso_url)

    except Exception as e:
        logger.error(f"Error initiating SAML login: {e}")
        raise HTTPException(status_code=500, detail=f"SAML login failed: {str(e)}")


@router.post("/acs")
async def saml_acs(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    SAML Assertion Consumer Service (ACS)

    This endpoint receives the SAML response from the IdP
    after successful authentication

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        JWT token or redirect to frontend with token
    """
    try:
        # Get form data
        form_data = await request.form()
        saml_response = form_data.get('SAMLResponse')
        relay_state = form_data.get('RelayState')

        if not saml_response:
            raise HTTPException(status_code=400, detail="No SAML response received")

        # Prepare request data
        request_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.headers.get('host', 'localhost:8000'),
            'server_port': request.url.port or 8000,
            'script_name': request.url.path,
            'get_data': {},
            'post_data': {'SAMLResponse': saml_response}
        }

        # Process SAML response
        user_data = saml_service.process_saml_response(
            saml_response,
            saml_service.prepare_flask_request(request_data)
        )

        if not user_data:
            raise HTTPException(status_code=401, detail="SAML authentication failed")

        # Get or create user
        user = auth_service.get_or_create_saml_user(
            db=db,
            saml_name_id=user_data['name_id'],
            saml_attributes=user_data['attributes']
        )

        if not user:
            raise HTTPException(status_code=500, detail="Failed to create/update user")

        # Update session index for logout
        user.saml_session_index = user_data.get('session_index')
        db.commit()

        # Generate JWT token
        access_token = auth_service.generate_user_token(user)

        logger.info(f"SAML authentication successful for: {user.username}")

        # If relay_state is provided, redirect there with token
        if relay_state:
            # Redirect to frontend with token in query params or hash
            redirect_url = f"{relay_state}?token={access_token}"
            return RedirectResponse(url=redirect_url)

        # Otherwise return JSON response
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing SAML response: {e}")
        raise HTTPException(status_code=500, detail=f"SAML processing failed: {str(e)}")


@router.get("/logout")
async def saml_logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    relay_state: str = None
):
    """
    Initiate SAML Single Logout (SLO)

    This endpoint initiates logout from the IdP

    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        relay_state: Optional URL to redirect after logout

    Returns:
        Redirect to IdP SLO URL
    """
    try:
        # Only SAML users can use SAML logout
        if current_user.auth_provider.value != "saml":
            raise HTTPException(
                status_code=400,
                detail="SAML logout only available for SAML users"
            )

        if not current_user.saml_name_id:
            raise HTTPException(
                status_code=400,
                detail="No SAML session found"
            )

        # Get SLO URL
        slo_url = saml_service.get_logout_url(
            name_id=current_user.saml_name_id,
            session_index=current_user.saml_session_index,
            relay_state=relay_state
        )

        logger.info(f"Initiating SAML logout for: {current_user.username}")
        return RedirectResponse(url=slo_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating SAML logout: {e}")
        raise HTTPException(status_code=500, detail=f"SAML logout failed: {str(e)}")


@router.get("/sls")
@router.post("/sls")
async def saml_sls(request: Request):
    """
    SAML Single Logout Service (SLS)

    This endpoint receives logout requests/responses from the IdP

    Args:
        request: FastAPI request object

    Returns:
        Logout confirmation
    """
    try:
        # Get query params or form data
        if request.method == "GET":
            data = dict(request.query_params)
        else:
            form_data = await request.form()
            data = dict(form_data)

        # Process logout request/response
        # This is simplified - in production you should validate the logout request

        logger.info("SAML logout completed")

        # Redirect to frontend logout page
        return RedirectResponse(url="/")

    except Exception as e:
        logger.error(f"Error processing SAML logout: {e}")
        raise HTTPException(status_code=500, detail=f"SAML logout processing failed: {str(e)}")


@router.get("/test")
async def test_saml_config():
    """
    Test SAML configuration

    This endpoint helps verify that SAML is configured correctly

    Returns:
        SAML configuration status
    """
    try:
        import os

        config_status = {
            "saml_enabled": True,
            "sp_entity_id": os.getenv("SAML_SP_ENTITY_ID", "NOT_SET"),
            "idp_entity_id": os.getenv("SAML_IDP_ENTITY_ID", "NOT_SET"),
            "idp_sso_url": os.getenv("SAML_IDP_SSO_URL", "NOT_SET"),
            "sp_base_url": os.getenv("SAML_SP_BASE_URL", "NOT_SET"),
        }

        # Check if required config is set
        missing_config = []
        if config_status["idp_entity_id"] == "NOT_SET":
            missing_config.append("SAML_IDP_ENTITY_ID")
        if config_status["idp_sso_url"] == "NOT_SET":
            missing_config.append("SAML_IDP_SSO_URL")

        config_status["configured"] = len(missing_config) == 0
        config_status["missing_config"] = missing_config

        return config_status

    except Exception as e:
        logger.error(f"Error checking SAML config: {e}")
        raise HTTPException(status_code=500, detail=f"Config check failed: {str(e)}")
