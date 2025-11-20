"""
Jenkins-inspired Queue Management System
Implements multi-state queue with priority handling and smart scheduling
Based on Jenkins' Queue.java architecture
"""
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib

from sqlalchemy.orm import Session

from app.models.jenkins_build import JenkinsBuild, BuildStatus
from app.models.jenkins_job import JenkinsJob
from app.models.jenkins_node import JenkinsNode, NodeStatus

logger = logging.getLogger(__name__)


class QueueItemState(str, Enum):
    """Queue item states - inspired by Jenkins Queue states"""
    WAITING = "waiting"  # In quiet period
    BLOCKED = "blocked"  # Blocked by resource/dependency
    BUILDABLE = "buildable"  # Ready to execute
    PENDING = "pending"  # Assigned to executor
    RUNNING = "running"  # Currently executing


class BuildPriority(int, Enum):
    """Build priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class QueueItem:
    """Represents an item in the build queue"""
    build_id: str
    job_id: str
    job_name: str
    build_number: int
    priority: int
    required_labels: List[str]
    state: QueueItemState
    queued_time: datetime
    quiet_until: Optional[datetime] = None  # Quiet period end time
    blocked_reason: Optional[str] = None
    assigned_node_id: Optional[str] = None
    max_concurrent_per_job: int = 1
    prefer_node_id: Optional[str] = None  # Node affinity

    def __lt__(self, other):
        """Compare for priority queue - higher priority first"""
        if self.priority != other.priority:
            return self.priority > other.priority
        # Same priority - FIFO
        return self.queued_time < other.queued_time


class JenkinsQueue:
    """
    Jenkins-inspired queue management system
    Implements multi-state queue with smart scheduling
    """

    def __init__(self, maintenance_interval: int = 1):
        # Queue collections
        self.waiting_list: List[QueueItem] = []  # In quiet period
        self.blocked: List[QueueItem] = []  # Blocked items
        self.buildables: List[QueueItem] = []  # Ready to execute (priority queue)
        self.pending: Dict[str, QueueItem] = {}  # build_id -> item

        # Tracking
        self.items_by_id: Dict[str, QueueItem] = {}  # build_id -> item
        self.running_builds: Dict[str, str] = {}  # build_id -> node_id
        self.job_build_counts: Dict[str, int] = defaultdict(int)  # job_id -> count

        # Synchronization
        self.lock = asyncio.Lock()
        self.maintenance_interval = maintenance_interval
        self.running = False

        # Metrics
        self.total_queued = 0
        self.total_completed = 0
        self.total_blocked = 0

    async def start(self):
        """Start queue maintenance"""
        if self.running:
            return
        self.running = True
        asyncio.create_task(self._maintenance_loop())
        logger.info("Jenkins Queue started")

    async def stop(self):
        """Stop queue maintenance"""
        self.running = False
        logger.info("Jenkins Queue stopped")

    async def enqueue(
        self,
        build_id: str,
        job_id: str,
        job_name: str,
        build_number: int,
        required_labels: List[str],
        priority: int = BuildPriority.NORMAL,
        quiet_period: int = 0,
        max_concurrent_per_job: int = 1,
        prefer_node_id: Optional[str] = None
    ) -> QueueItem:
        """
        Add a build to the queue

        Args:
            build_id: Build UUID
            job_id: Job UUID
            job_name: Job name
            build_number: Build number
            required_labels: Required node labels
            priority: Build priority (higher = more important)
            quiet_period: Seconds to wait before building
            max_concurrent_per_job: Max concurrent builds for this job
            prefer_node_id: Preferred node for execution (affinity)

        Returns:
            QueueItem
        """
        async with self.lock:
            # Create queue item
            now = datetime.utcnow()
            quiet_until = now + timedelta(seconds=quiet_period) if quiet_period > 0 else None

            item = QueueItem(
                build_id=build_id,
                job_id=job_id,
                job_name=job_name,
                build_number=build_number,
                priority=priority,
                required_labels=required_labels,
                state=QueueItemState.WAITING if quiet_until else QueueItemState.BUILDABLE,
                queued_time=now,
                quiet_until=quiet_until,
                max_concurrent_per_job=max_concurrent_per_job,
                prefer_node_id=prefer_node_id
            )

            # Add to appropriate list
            if quiet_until:
                self.waiting_list.append(item)
                logger.info(f"Build #{build_number} added to waiting list (quiet period: {quiet_period}s)")
            else:
                self._add_to_buildables(item)
                logger.info(f"Build #{build_number} added to buildables")

            self.items_by_id[build_id] = item
            self.total_queued += 1

            return item

    async def get_next_buildable(self, db: Session) -> Optional[QueueItem]:
        """
        Get next buildable item that can be executed
        Returns None if no buildable items or no available nodes
        """
        async with self.lock:
            if not self.buildables:
                return None

            # Sort buildables by priority
            self.buildables.sort()

            # Try each buildable item
            for item in self.buildables[:]:
                # Check if blocked
                blocked_reason = await self._check_if_blocked(item, db)
                if blocked_reason:
                    # Move to blocked
                    self.buildables.remove(item)
                    item.state = QueueItemState.BLOCKED
                    item.blocked_reason = blocked_reason
                    self.blocked.append(item)
                    self.total_blocked += 1
                    logger.info(f"Build #{item.build_number} blocked: {blocked_reason}")
                    continue

                # Item is buildable, remove from list and return
                self.buildables.remove(item)
                item.state = QueueItemState.PENDING
                self.pending[item.build_id] = item
                logger.info(f"Build #{item.build_number} ready for execution")
                return item

            return None

    async def mark_running(self, build_id: str, node_id: str):
        """Mark a build as running on a node"""
        async with self.lock:
            if build_id in self.pending:
                item = self.pending.pop(build_id)
                item.state = QueueItemState.RUNNING
                item.assigned_node_id = node_id
                self.running_builds[build_id] = node_id
                self.job_build_counts[item.job_id] += 1
                logger.info(f"Build #{item.build_number} now running on node {node_id}")

    async def mark_completed(self, build_id: str):
        """Mark a build as completed and remove from queue"""
        async with self.lock:
            if build_id in self.items_by_id:
                item = self.items_by_id.pop(build_id)

                if build_id in self.running_builds:
                    self.running_builds.pop(build_id)

                if item.job_id in self.job_build_counts:
                    self.job_build_counts[item.job_id] = max(0, self.job_build_counts[item.job_id] - 1)

                self.total_completed += 1
                logger.info(f"Build #{item.build_number} completed and removed from queue")

    async def abort_build(self, build_id: str):
        """Abort a build and remove from queue"""
        async with self.lock:
            if build_id not in self.items_by_id:
                return False

            item = self.items_by_id.pop(build_id)

            # Remove from appropriate list
            if item.state == QueueItemState.WAITING and item in self.waiting_list:
                self.waiting_list.remove(item)
            elif item.state == QueueItemState.BLOCKED and item in self.blocked:
                self.blocked.remove(item)
            elif item.state == QueueItemState.BUILDABLE and item in self.buildables:
                self.buildables.remove(item)
            elif item.state == QueueItemState.PENDING and build_id in self.pending:
                self.pending.pop(build_id)
            elif item.state == QueueItemState.RUNNING and build_id in self.running_builds:
                self.running_builds.pop(build_id)
                if item.job_id in self.job_build_counts:
                    self.job_build_counts[item.job_id] = max(0, self.job_build_counts[item.job_id] - 1)

            logger.info(f"Build #{item.build_number} aborted and removed from queue")
            return True

    def _add_to_buildables(self, item: QueueItem):
        """Add item to buildables list (priority queue)"""
        item.state = QueueItemState.BUILDABLE
        self.buildables.append(item)
        self.buildables.sort()  # Sort by priority

    async def _check_if_blocked(self, item: QueueItem, db: Session) -> Optional[str]:
        """
        Check if a build item is blocked
        Returns blocked reason or None if not blocked
        """
        # Check 1: Max concurrent builds per job
        if item.max_concurrent_per_job > 0:
            current_count = self.job_build_counts.get(item.job_id, 0)
            if current_count >= item.max_concurrent_per_job:
                return f"Job '{item.job_name}' already has {current_count} concurrent builds (max: {item.max_concurrent_per_job})"

        # Check 2: Node availability
        from app.services.jenkins_pool import connection_pool
        available_node = connection_pool.acquire_node(db, labels=item.required_labels, dry_run=True)
        if not available_node:
            return f"No available nodes with labels: {item.required_labels}"

        # Check 3: Preferred node availability (if specified)
        if item.prefer_node_id:
            node = db.get(JenkinsNode, item.prefer_node_id)
            if node and node.status == NodeStatus.ONLINE and node.current_executors < node.max_executors:
                # Preferred node is available, not blocked
                pass
            else:
                # Preferred node not available, but we can use others
                pass

        return None  # Not blocked

    async def _maintenance_loop(self):
        """
        Background maintenance task
        - Moves items from waiting_list to buildables after quiet period
        - Re-evaluates blocked items
        - Cleans up stale items
        """
        while self.running:
            try:
                await asyncio.sleep(self.maintenance_interval)
                await self._maintain()
            except Exception as e:
                logger.error(f"Error in queue maintenance: {e}")

    async def _maintain(self):
        """Perform queue maintenance"""
        async with self.lock:
            now = datetime.utcnow()

            # 1. Move items from waiting_list to buildables
            for item in self.waiting_list[:]:
                if item.quiet_until and now >= item.quiet_until:
                    self.waiting_list.remove(item)
                    self._add_to_buildables(item)
                    logger.info(f"Build #{item.build_number} moved to buildables (quiet period ended)")

            # 2. Re-evaluate blocked items
            # Note: We'll re-evaluate blocked items when get_next_buildable is called
            # For now, periodically move them back to buildables to retry
            if len(self.blocked) > 0:
                # Move some blocked items back to buildables to retry
                items_to_retry = self.blocked[:min(5, len(self.blocked))]
                for item in items_to_retry:
                    self.blocked.remove(item)
                    item.blocked_reason = None
                    self._add_to_buildables(item)
                    logger.debug(f"Build #{item.build_number} moved from blocked to buildables for retry")

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self.lock:
            return {
                "total_queued": self.total_queued,
                "total_completed": self.total_completed,
                "total_blocked": self.total_blocked,
                "waiting_count": len(self.waiting_list),
                "blocked_count": len(self.blocked),
                "buildables_count": len(self.buildables),
                "pending_count": len(self.pending),
                "running_count": len(self.running_builds),
                "waiting_items": [
                    {
                        "build_id": item.build_id,
                        "job_name": item.job_name,
                        "build_number": item.build_number,
                        "priority": item.priority,
                        "quiet_until": item.quiet_until.isoformat() if item.quiet_until else None
                    }
                    for item in self.waiting_list
                ],
                "blocked_items": [
                    {
                        "build_id": item.build_id,
                        "job_name": item.job_name,
                        "build_number": item.build_number,
                        "blocked_reason": item.blocked_reason
                    }
                    for item in self.blocked
                ],
                "buildables_items": [
                    {
                        "build_id": item.build_id,
                        "job_name": item.job_name,
                        "build_number": item.build_number,
                        "priority": item.priority
                    }
                    for item in self.buildables
                ],
                "running_builds": [
                    {
                        "build_id": build_id,
                        "node_id": node_id
                    }
                    for build_id, node_id in self.running_builds.items()
                ]
            }


# Global queue instance
jenkins_queue = JenkinsQueue()
