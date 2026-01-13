"""
Device Nodes API Proxy
Proxies requests to the device nodes HTTP API to avoid mixed content errors
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Device nodes API configuration from settings
DEVICE_NODES_API_BASE_URL = settings.DEVICE_NODES_API_URL


@router.get("/nodes/proxy/nodes")
async def proxy_get_nodes():
    """Proxy GET /nodes request to device nodes API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DEVICE_NODES_API_BASE_URL}/nodes",
                timeout=10.0
            )
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to device nodes API: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to device nodes API"
        )
    except Exception as e:
        logger.error(f"Unexpected error in proxy: {e}")
        raise HTTPException(status_code=500, detail="Internal proxy error")


@router.get("/nodes/proxy/nodes/available")
async def proxy_get_available_nodes():
    """Proxy GET /nodes/available request to device nodes API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DEVICE_NODES_API_BASE_URL}/nodes/available",
                timeout=10.0
            )
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to device nodes API: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to device nodes API"
        )
    except Exception as e:
        logger.error(f"Unexpected error in proxy: {e}")
        raise HTTPException(status_code=500, detail="Internal proxy error")


@router.api_route("/nodes/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_device_nodes_api(path: str, request: Request):
    """
    Generic proxy for any device nodes API endpoint

    Args:
        path: The path to proxy to the device nodes API
        request: The incoming request

    Returns:
        Proxied response from the device nodes API
    """
    try:
        # Build the target URL
        target_url = f"{DEVICE_NODES_API_BASE_URL}/{path}"

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Forward the request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in ["host", "connection"]
                },
                params=request.query_params,
                timeout=30.0
            )

            # Return the response
            try:
                content = response.json()
                return JSONResponse(
                    content=content,
                    status_code=response.status_code
                )
            except:
                # If response is not JSON, return as text
                return JSONResponse(
                    content={"data": response.text},
                    status_code=response.status_code
                )

    except httpx.RequestError as e:
        logger.error(f"Error proxying request to device nodes API: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to device nodes API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in proxy: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal proxy error: {str(e)}"
        )
