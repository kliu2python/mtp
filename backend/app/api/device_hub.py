"""
DeviceHub Proxy API - Reverse proxy to devicehub.qa.fortinet-us.com
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter()

DEVICE_HUB_URL = "https://devicehub.qa.fortinet-us.com"


@router.get("/device-hub/{path:path}")
async def proxy_device_hub(request: Request, path: str):
    """
    Proxy requests to DeviceHub
    """
    try:
        # Get query parameters
        query_params = dict(request.query_params)

        async with httpx.AsyncClient() as client:
            # Proxy the request to DeviceHub
            url = f"{DEVICE_HUB_URL}/{path}"

            response = await client.get(
                url,
                params=query_params,
                headers={
                    "User-Agent": request.headers.get("User-Agent", ""),
                },
                timeout=30.0
            )

            # Return the response
            return StreamingResponse(
                response.iter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to DeviceHub: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxying request: {str(e)}")
