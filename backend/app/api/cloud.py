import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

logger = logging.getLogger(__name__)


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
