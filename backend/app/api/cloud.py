import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cloud_service import CloudService
from app.services.fic_ops import FICTokenOps, session_manager

router = APIRouter()

logger = logging.getLogger(__name__)


class CloudServiceCreate(BaseModel):
    """Payload for creating a cloud service entry."""

    name: Optional[str] = None
    server_ip: Optional[str] = None
    server_dns: Optional[str] = None
    client_ip: str
    server_version: Optional[str] = None

    @field_validator("server_ip", "server_dns", mode="before")
    def empty_string_to_none(cls, value: Optional[str]):  # noqa: D401, ANN001
        """Normalize empty strings to None so they are not persisted."""
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def validate_addresses(self):  # noqa: D401
        """Require at least one of server_ip or server_dns to be provided."""
        if not (self.server_ip or self.server_dns):
            raise ValueError("Either server_ip or server_dns must be provided")
        return self


class FICLoginRequest(BaseModel):
    """Payload for FIC login request"""
    jumpbox_host: str
    jumpbox_user: str
    jumpbox_password: str
    target_host: str
    target_user: str
    target_key_file: str
    expires_in_hours: Optional[int] = 24


class FICConfigUpdateRequest(BaseModel):
    """Payload for FIC configuration update request"""
    format: str


class FICSandboxUpdateRequest(BaseModel):
    """Payload for FIC sandbox update request"""
    value: str


class FICMonitoringStartRequest(BaseModel):
    """Payload for FIC monitoring start request"""
    frontend_url: Optional[str] = "https://frontend.fortitoken.local/health"
    backend_url: Optional[str] = "https://backend.fortitoken.local/health"
    interval: Optional[int] = 60


class FICServerCheckRequest(BaseModel):
    """Payload for FIC server check request"""
    url: str
    type: Optional[str] = "unknown"


def get_session(session_id: str = Header(None, alias="Authorization")):
    """Get session from Authorization header"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # Extract session ID from "Bearer <token>" format
    if session_id.startswith("Bearer "):
        session_id = session_id[7:]

    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return session


@router.get("/version")
async def get_cloud_version(client_ip: str):
    """Fetch the cloud version that matches the provided client IP.

    The upstream status endpoint returns a list of results containing the
    selected_ip and version information. We match the provided client IP to the
    selected_ip and return the associated ftc_server version (or ftc_portal as a
    fallback).
    """

    if not client_ip:
        raise HTTPException(status_code=400, detail="client_ip is required")

    status_url = "https://10.160.83.127/status/atlassian-summary"

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(status_url)
            response.raise_for_status()
            payload: Dict[str, Any] = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Cloud status endpoint returned HTTP %s", exc.response.status_code)
        raise HTTPException(status_code=exc.response.status_code, detail="Failed to fetch cloud status")
    except httpx.RequestError as exc:
        logger.error("Error calling cloud status endpoint: %s", exc)
        raise HTTPException(status_code=503, detail="Unable to reach cloud status endpoint")
    except Exception:
        logger.exception("Unexpected error when parsing cloud status response")
        raise HTTPException(status_code=500, detail="Unexpected error while fetching cloud status")

    results = payload.get("results", [])

    for entry in results:
        if not entry or not entry.get("ok"):
            continue

        if entry.get("selected_ip") == client_ip:
            version_info = entry.get("json") or {}
            version = version_info.get("ftc_server") or version_info.get("ftc_portal")

            if version:
                return {"version": version, "matched_host": entry.get("selected_host")}

            break

    raise HTTPException(status_code=404, detail="No matching cloud service found for the provided client IP")


@router.get("/services")
async def list_cloud_services(db: Session = Depends(get_db)):
    """Return all configured cloud services."""
    services: List[CloudService] = (
        db.query(CloudService).order_by(CloudService.created_at.desc()).all()
    )
    return {"cloud_services": [service.to_dict() for service in services]}


@router.post("/services", status_code=201)
async def create_cloud_service(
    payload: CloudServiceCreate, db: Session = Depends(get_db)
):
    """Create and persist a new cloud service entry."""
    service = CloudService(
        name=payload.name or payload.server_dns or payload.server_ip or payload.client_ip,
        server_ip=payload.server_ip,
        server_dns=payload.server_dns,
        client_ip=payload.client_ip,
        server_version=payload.server_version,
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return {"cloud_service": service.to_dict()}


@router.delete("/services/{service_id}")
async def delete_cloud_service(service_id: str, db: Session = Depends(get_db)):
    """Remove a cloud service from the test platform."""
    service = db.query(CloudService).filter(CloudService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Cloud service not found")

    db.delete(service)
    db.commit()

    return {"message": "Cloud service deleted"}


# FortiToken Cloud Ops endpoints

@router.get("/fic/health")
async def fic_health_check():
    """Health check endpoint for FortiToken Cloud Ops"""
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'FortiToken Cloud Ops API',
        'active_sessions': len(session_manager.sessions),
    }


@router.post("/fic/auth/login")
async def fic_login(payload: FICLoginRequest):
    """Create new session with SSH configuration"""
    ssh_config = {
        'jumpbox_host': payload.jumpbox_host,
        'jumpbox_user': payload.jumpbox_user,
        'jumpbox_password': payload.jumpbox_password,
        'target_host': payload.target_host,
        'target_user': payload.target_user,
        'target_key_file': payload.target_key_file,
    }

    session_id, error = session_manager.create_session(ssh_config, payload.expires_in_hours)

    if error:
        raise HTTPException(status_code=500, detail=error)

    return {
        'success': True,
        'message': 'Session created successfully',
        'session_id': session_id,
        'bearer_token': session_id,
        'expires_in_hours': payload.expires_in_hours,
    }


@router.post("/fic/auth/logout")
async def fic_logout(session=Depends(get_session)):
    """Delete current session"""
    session_manager.delete_session(session.session_id)
    return {'success': True, 'message': 'Session deleted successfully'}


@router.get("/fic/auth/sessions")
async def fic_list_sessions():
    """List all active sessions (admin endpoint)"""
    return {
        'sessions': session_manager.list_sessions(),
        'total_sessions': len(session_manager.sessions),
    }


@router.get("/fic/auth/session")
async def fic_get_session_info(session=Depends(get_session)):
    """Get current session information"""
    return session.get_session_info()


@router.get("/fic/token-format")
async def fic_get_token_format_version(session=Depends(get_session)):
    """Get current token_format_version configuration"""
    result = session.ops_manager.get_token_format_version()
    return result


@router.put("/fic/token-format")
async def fic_update_token_format_version(
    payload: FICConfigUpdateRequest,
    session=Depends(get_session)
):
    """Update token_format_version configuration"""
    result = session.ops_manager.update_token_format_version(payload.format)

    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


@router.post("/fic/service/restart")
async def fic_restart_service(session=Depends(get_session)):
    """Restart FortiToken service"""
    result = session.ops_manager.restart_service()

    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])

    return result


@router.post("/fic/monitoring/start")
async def fic_start_monitoring(
    payload: FICMonitoringStartRequest,
    session=Depends(get_session)
):
    """Start server monitoring"""
    result = session.ops_manager.start_monitoring(
        payload.frontend_url, payload.backend_url, payload.interval
    )
    return result


@router.post("/fic/monitoring/stop")
async def fic_stop_monitoring(session=Depends(get_session)):
    """Stop server monitoring"""
    result = session.ops_manager.stop_monitoring()
    return result


@router.get("/fic/monitoring/status")
async def fic_get_monitoring_status(session=Depends(get_session)):
    """Get monitoring status"""
    result = session.ops_manager.get_current_status()
    return result


@router.post("/fic/server/check")
async def fic_manual_server_check(
    payload: FICServerCheckRequest,
    session=Depends(get_session)
):
    """Manual server status check"""
    result = session.ops_manager.check_server_status(payload.type, payload.url)
    return result


@router.put("/fic/push/sandbox")
async def fic_update_use_sandbox(
    payload: FICSandboxUpdateRequest,
    session=Depends(get_session)
):
    """Update use_sandbox under [push] to True/False"""
    result = session.ops_manager.update_use_sandbox(payload.value)
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    return result


@router.get("/fic/push/sandbox")
async def fic_get_use_sandbox_status(session=Depends(get_session)):
    """Get the current use_sandbox status under [push]"""
    result = session.ops_manager.get_use_sandbox_status()
    return result


@router.get("/fic/decode")
async def fic_decode_token_information(token: str):
    """Decode token information"""
    if not token:
        raise HTTPException(status_code=400, detail="Missing token parameter")

    result = FICTokenOps().decode_token(token)
    return result
