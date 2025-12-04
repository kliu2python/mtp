import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cloud_service import CloudService

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
