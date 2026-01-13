"""
Device Monitor Service
- Monitors health of DeviceStreamService
- Does NOT fetch or update devices
"""

import asyncio
import logging
from app.services.device_stream_service import device_stream_service

logger = logging.getLogger(__name__)


class DeviceMonitor:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        logger.info("DeviceMonitor started")

        while self._running:
            try:
                status = device_stream_service.get_cache_status()

                if not status["has_data"]:
                    logger.warning("Device cache is empty")

                elif status["cache_age_seconds"] and status["cache_age_seconds"] > 10:
                    logger.warning(
                        f"Device cache stale: {status['cache_age_seconds']:.1f}s"
                    )

                else:
                    logger.debug(
                        f"Device cache OK: {status['cache_size']} devices"
                    )

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                logger.info("DeviceMonitor cancelled")
                break

            except Exception:
                logger.exception("Unexpected error in DeviceMonitor")
                await asyncio.sleep(5)

        logger.info("DeviceMonitor stopped")

    def run_background(self):
        logger.info(f"background task starting")
        if not self._task:
            logger.info(f"background task is starting")
            self._task = asyncio.create_task(self.start())
            logger.info(f"background task started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


device_monitor = DeviceMonitor()
