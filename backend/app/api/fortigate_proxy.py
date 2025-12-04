"""
FortiGate reverse proxy endpoints.
"""
from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx

from app.core.config import settings


router = APIRouter()

FRAME_BLOCKING_HEADERS = {
    "x-frame-options",
    "content-security-policy",
    "frame-ancestors",
}

REQUEST_HEADER_FILTER = {
    "host",
    "content-length",
}


@router.api_route("/fgt/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_fgt(full_path: str, request: Request):
    """Reverse proxy FortiGate UI and strip iframe-blocking headers."""
    target_url = f"{settings.FGT_BASE_URL.rstrip('/')}/{full_path}"

    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    forwarded_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in REQUEST_HEADER_FILTER
    }

    async with httpx.AsyncClient(
        verify=settings.FGT_VERIFY_SSL,
        follow_redirects=True,
    ) as client:
        proxied = await client.request(
            method=request.method,
            url=target_url,
            content=await request.body(),
            headers=forwarded_headers,
        )

    response_headers = {
        key: value
        for key, value in proxied.headers.items()
        if key.lower() not in FRAME_BLOCKING_HEADERS
    }

    response_headers["Content-Security-Policy"] = "frame-ancestors *"

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
    )
