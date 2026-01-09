"""
Device Stream Service
- Consumes devicehub streaming API (chunked `data:` frames)
- Maintains latest device snapshot in memory
- Safe for FastAPI lifespan background task
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

import aiohttp
from aiohttp import ClientError, ClientTimeout

logger = logging.getLogger(__name__)


class DeviceStreamService:
    def __init__(self):
        self.streaming_url = "https://devicehub.qa.fortinet-us.com/available-devices"
        self.workspace_id = "6941ce4ccc22ee3ac0a3e553"

        self.devices_cache: List[Dict] = []
        self.cache_timestamp: Optional[datetime] = None
        self.cache_lock = asyncio.Lock()

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # =========================
    # Lifecycle
    # =========================

    async def start(self):
        """Start consuming device stream (run forever)."""
        logger.info("Starting DeviceStreamService")

        timeout = ClientTimeout(
            total=None,          # 🔥 stream must not have total timeout
            connect=10,
            sock_read=None       # 🔥 allow infinite read
        )

        while not self._stop_event.is_set():
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    url = f"{self.streaming_url}?workspaceId={self.workspace_id}"
                    logger.info(f"Connecting to device stream: {url}")

                    async with session.get(url) as response:
                        
                        logger.info(f"response is {response}")
                        if response.status != 200:
                            logger.error(f"Device stream HTTP {response.status}")
                            await asyncio.sleep(5)
                            continue

                        async for raw_line in response.content:
                            if self._stop_event.is_set():
                                break

                            if not raw_line:
                                continue

                            line = raw_line.decode(errors="ignore").strip()
                            if not line.startswith("data:"):
                                continue

                            payload = line[5:].strip()
                            try:
                                devices = json.loads(payload)
                            except json.JSONDecodeError:
                                logger.warning("Failed to parse device stream JSON")
                                continue

                            async with self.cache_lock:
                                self.devices_cache = devices
                                self.cache_timestamp = datetime.utcnow()

            except asyncio.CancelledError:
                logger.info("DeviceStreamService cancelled")
                break

            except (ClientError, OSError) as e:
                logger.warning(f"Device stream connection error: {e}")
                await asyncio.sleep(3)

            except Exception:
                logger.exception("Unexpected error in DeviceStreamService")
                await asyncio.sleep(5)

        logger.info("DeviceStreamService stopped")

    async def stop(self):
        """Stop the stream gracefully."""
        logger.info("Stopping DeviceStreamService")
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def run_background(self):
        """Create background task (used in FastAPI lifespan)."""
        if not self._task:
            self._task = asyncio.create_task(self.start())

    # =========================
    # Read API (Fast)
    # =========================

    async def get_cached_devices(self) -> List[Dict]:
        async with self.cache_lock:
            return list(self.devices_cache)

    def get_cache_age_seconds(self) -> Optional[float]:
        if self.cache_timestamp:
            return (datetime.utcnow() - self.cache_timestamp).total_seconds()
        return None

    def get_cache_status(self) -> Dict:
        return {
            "cache_size": len(self.devices_cache),
            "cache_age_seconds": self.get_cache_age_seconds(),
            "cache_timestamp": self.cache_timestamp.isoformat() if self.cache_timestamp else None,
            "has_data": bool(self.devices_cache),
        }

    async def get_device_summary(self) -> Dict:
        devices = await self.get_cached_devices()

        ios = sum(1 for d in devices if d.get("info", {}).get("os") == "ios")
        android = sum(1 for d in devices if d.get("info", {}).get("os") == "android")
        available = sum(1 for d in devices if d.get("available"))
        in_use = sum(1 for d in devices if d.get("in_use"))

        return {
            "total": len(devices),
            "available": available,
            "in_use": in_use,
            "by_platform": {
                "iOS": ios,
                "Android": android,
            },
        }


# Singleton
device_stream_service = DeviceStreamService()
