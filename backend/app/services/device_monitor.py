"""
Device Monitor Service
- Monitors health of devices from database
- DeviceHub stream service removed - now accessed via external link
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class DeviceMonitor:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        logger.info("DeviceMonitor started (DeviceHub stream removed - using external link)")

        while self._running:
            try:
                # DeviceHub stream service removed - monitoring disabled
                # DeviceHub is now accessed via external link: https://devicehub.qa.fortinet-us.com
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("DeviceMonitor cancelled")
                break

            except Exception:
                logger.exception("Unexpected error in DeviceMonitor")
                await asyncio.sleep(60)

        logger.info("DeviceMonitor stopped")

    def run_background(self):
        logger.info("DeviceMonitor background task starting")
        if not self._task:
            logger.info("DeviceMonitor background task started")
            self._task = asyncio.create_task(self.start())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


device_monitor = DeviceMonitor()
