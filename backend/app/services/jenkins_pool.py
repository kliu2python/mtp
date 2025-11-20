"""
Jenkins Slave Node Connection Pool Service
Manages a pool of slave nodes for distributed test execution
"""
import asyncio
import logging
import subprocess
import time
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from threading import Lock
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.jenkins_node import JenkinsNode, NodeStatus

logger = logging.getLogger(__name__)


class NodeConnectionPool:
    """Manages connection pool for Jenkins slave nodes"""

    def __init__(self):
        self._lock = Lock()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # node_id -> session info

    def test_ssh_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        ssh_key: Optional[str] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Test SSH connection to a slave node

        Returns:
            dict with keys: success (bool), message (str), latency (float)
        """
        start_time = time.time()

        try:
            # Build SSH command
            ssh_cmd = [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", f"ConnectTimeout={timeout}",
                "-p", str(port),
            ]

            # Add authentication method
            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            elif password:
                # Use sshpass for password authentication
                ssh_cmd = ["sshpass", "-p", password] + ssh_cmd
            else:
                return {
                    "success": False,
                    "message": "Either password or SSH key must be provided",
                    "latency": 0
                }

            # Add target
            ssh_cmd.append(f"{username}@{host}")
            ssh_cmd.append("echo 'Connection test successful'")

            # Execute SSH command
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            latency = time.time() - start_time

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Connection successful",
                    "latency": round(latency, 3)
                }
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return {
                    "success": False,
                    "message": f"Connection failed: {error_msg}",
                    "latency": round(latency, 3)
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"Connection timeout after {timeout} seconds",
                "latency": timeout
            }
        except FileNotFoundError as e:
            return {
                "success": False,
                "message": f"SSH client not found: {str(e)}",
                "latency": 0
            }
        except Exception as e:
            logger.error(f"Error testing SSH connection to {host}:{port}: {e}")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "latency": time.time() - start_time
            }

    def get_system_resources(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        ssh_key: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get system resource usage from a node

        Returns:
            dict with keys: cpu_usage, memory_usage, disk_usage (all in percentage)
        """
        try:
            # Build SSH command to get system stats
            commands = [
                # CPU usage (1 - idle%)
                "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'",
                # Memory usage
                "free | grep Mem | awk '{print int($3/$2 * 100)}'",
                # Disk usage
                "df -h / | tail -1 | awk '{print int($5)}'"
            ]

            full_cmd = " && ".join(commands)

            # Build SSH command
            ssh_cmd = [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=5",
                "-p", str(port),
            ]

            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            elif password:
                ssh_cmd = ["sshpass", "-p", password] + ssh_cmd

            ssh_cmd.append(f"{username}@{host}")
            ssh_cmd.append(full_cmd)

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 3:
                    return {
                        "cpu_usage": int(float(lines[0])),
                        "memory_usage": int(lines[1]),
                        "disk_usage": int(lines[2])
                    }

        except Exception as e:
            logger.error(f"Error getting system resources from {host}:{port}: {e}")

        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0
        }

    def acquire_node(
        self,
        db: Session,
        labels: Optional[List[str]] = None,
        prefer_node_id: Optional[str] = None,
        job_name: Optional[str] = None,
        dry_run: bool = False
    ) -> Optional[JenkinsNode]:
        """
        Acquire an available node from the pool using smart load balancing
        Inspired by Jenkins' consistent hash and load balancing strategies

        Args:
            db: Database session
            labels: Optional list of required labels (e.g., ["android", "linux"])
            prefer_node_id: Preferred node ID (affinity)
            job_name: Job name for consistent hashing
            dry_run: If True, don't actually acquire, just check availability

        Returns:
            Available JenkinsNode or None
        """
        with self._lock:
            # Build query for available nodes
            query = select(JenkinsNode).where(
                JenkinsNode.enabled == True,
                JenkinsNode.status.in_([NodeStatus.ONLINE, NodeStatus.TESTING, NodeStatus.BUSY]),
            )

            # Filter by labels if specified
            if labels:
                for label in labels:
                    query = query.where(JenkinsNode.labels.contains([label]))

            # Get all matching nodes
            all_nodes = db.execute(query).scalars().all()

            # Filter nodes with available executors
            available_nodes = [n for n in all_nodes if n.current_executors < n.max_executors]

            if not available_nodes:
                logger.warning(f"No available nodes found for labels: {labels}")
                return None

            # Strategy 1: Prefer specified node if available
            if prefer_node_id:
                preferred = next((n for n in available_nodes if str(n.id) == prefer_node_id), None)
                if preferred:
                    logger.info(f"Using preferred node {preferred.name}")
                    if not dry_run:
                        preferred.current_executors += 1
                        preferred.status = NodeStatus.BUSY
                        db.commit()
                        db.refresh(preferred)
                    return preferred

            # Strategy 2: Use consistent hashing if job_name provided
            if job_name:
                selected = self._consistent_hash_node_selection(available_nodes, job_name)
                logger.info(f"Selected node {selected.name} via consistent hashing for job '{job_name}'")
                if not dry_run:
                    selected.current_executors += 1
                    selected.status = NodeStatus.BUSY
                    db.commit()
                    db.refresh(selected)
                return selected

            # Strategy 3: Load-based selection (least loaded first)
            selected = self._load_balanced_selection(available_nodes)
            logger.info(f"Selected node {selected.name} via load balancing")

            if not dry_run:
                selected.current_executors += 1
                selected.status = NodeStatus.BUSY
                db.commit()
                db.refresh(selected)
                logger.info(f"Acquired node {selected.name} ({selected.current_executors}/{selected.max_executors} executors)")

            return selected

    def _consistent_hash_node_selection(self, nodes: List[JenkinsNode], job_name: str) -> JenkinsNode:
        """
        Select node using consistent hashing
        Inspired by Jenkins LoadBalancer consistent hash strategy
        This ensures the same job tends to run on the same node

        Args:
            nodes: List of available nodes
            job_name: Job name for hashing

        Returns:
            Selected node
        """
        # Hash the job name
        hash_value = int(hashlib.md5(job_name.encode()).hexdigest(), 16)

        # Calculate node scores based on hash and availability
        node_scores = []
        for node in nodes:
            # Factor in executor availability (more available = higher score)
            available_executors = node.max_executors - node.current_executors
            availability_weight = available_executors / node.max_executors

            # Combine hash with availability (100x weight for availability)
            node_hash = int(hashlib.md5(f"{node.name}:{job_name}".encode()).hexdigest(), 16)
            score = (node_hash % 1000) + (availability_weight * 100000)

            node_scores.append((score, node))

        # Sort by score and return highest
        node_scores.sort(key=lambda x: x[0], reverse=True)
        return node_scores[0][1]

    def _load_balanced_selection(self, nodes: List[JenkinsNode]) -> JenkinsNode:
        """
        Select node based on current load
        Considers: executor utilization, CPU, memory, test success rate

        Args:
            nodes: List of available nodes

        Returns:
            Best node based on load
        """
        node_scores = []

        for node in nodes:
            # Calculate executor utilization (lower is better)
            executor_util = node.current_executors / node.max_executors if node.max_executors > 0 else 1.0

            # Calculate resource usage (lower is better)
            cpu_load = node.cpu_usage / 100.0 if node.cpu_usage else 0.5
            memory_load = node.memory_usage / 100.0 if node.memory_usage else 0.5

            # Calculate success rate (higher is better)
            total_tests = node.total_tests_executed
            success_rate = (node.total_tests_passed / total_tests) if total_tests > 0 else 0.5

            # Combined score (lower is better for executor/cpu/memory, higher for success)
            # Weights: executor=40%, cpu=20%, memory=20%, success=20%
            score = (
                (1.0 - executor_util) * 40 +  # More available executors = better
                (1.0 - cpu_load) * 20 +         # Lower CPU = better
                (1.0 - memory_load) * 20 +      # Lower memory = better
                success_rate * 20                # Higher success rate = better
            )

            node_scores.append((score, node))
            logger.debug(
                f"Node {node.name}: score={score:.2f} "
                f"(exec_util={executor_util:.2f}, cpu={cpu_load:.2f}, "
                f"mem={memory_load:.2f}, success={success_rate:.2f})"
            )

        # Sort by score (highest first) and return best
        node_scores.sort(key=lambda x: x[0], reverse=True)
        return node_scores[0][1]

    def release_node(self, db: Session, node_id: str):
        """
        Release a node back to the pool

        Args:
            db: Database session
            node_id: UUID of the node to release
        """
        with self._lock:
            node = db.get(JenkinsNode, node_id)
            if node:
                node.current_executors = max(0, node.current_executors - 1)

                # Update status based on executor count
                if node.current_executors == 0:
                    node.status = NodeStatus.ONLINE
                else:
                    node.status = NodeStatus.BUSY

                db.commit()
                db.refresh(node)
                logger.info(f"Released node {node.name} ({node.current_executors}/{node.max_executors} executors)")

    def update_node_metrics(
        self,
        db: Session,
        node_id: str,
        test_passed: bool,
        test_duration: int
    ):
        """
        Update node metrics after test execution

        Args:
            db: Database session
            node_id: UUID of the node
            test_passed: Whether the test passed
            test_duration: Test duration in seconds
        """
        node = db.get(JenkinsNode, node_id)
        if node:
            node.total_tests_executed += 1
            if test_passed:
                node.total_tests_passed += 1
            else:
                node.total_tests_failed += 1

            # Update average test duration
            total_duration = node.average_test_duration * (node.total_tests_executed - 1)
            node.average_test_duration = int((total_duration + test_duration) / node.total_tests_executed)

            db.commit()
            db.refresh(node)

    async def health_check_all_nodes(self, db: Session):
        """
        Perform health check on all nodes and update their status

        Args:
            db: Database session
        """
        nodes = db.execute(select(JenkinsNode)).scalars().all()

        for node in nodes:
            if not node.enabled:
                continue

            # Test connection
            result = self.test_ssh_connection(
                host=node.host,
                port=node.port,
                username=node.username,
                password=node.password,
                ssh_key=node.ssh_key,
                timeout=5
            )

            # Update node status
            if result["success"]:
                if node.status == NodeStatus.OFFLINE or node.status == NodeStatus.ERROR:
                    node.status = NodeStatus.ONLINE
                node.last_ping_time = datetime.utcnow()
                node.last_error = None

                # Get system resources
                resources = self.get_system_resources(
                    host=node.host,
                    port=node.port,
                    username=node.username,
                    password=node.password,
                    ssh_key=node.ssh_key
                )
                node.cpu_usage = resources["cpu_usage"]
                node.memory_usage = resources["memory_usage"]
                node.disk_usage = resources["disk_usage"]
            else:
                node.status = NodeStatus.ERROR
                node.last_error = result["message"]

            db.commit()

        logger.info(f"Health check completed for {len(nodes)} nodes")

    def get_pool_stats(self, db: Session) -> Dict[str, Any]:
        """
        Get statistics about the connection pool

        Returns:
            dict with pool statistics
        """
        nodes = db.execute(select(JenkinsNode)).scalars().all()

        total_nodes = len(nodes)
        online_nodes = sum(1 for n in nodes if n.status == NodeStatus.ONLINE)
        busy_nodes = sum(1 for n in nodes if n.status == NodeStatus.BUSY)
        offline_nodes = sum(1 for n in nodes if n.status == NodeStatus.OFFLINE)
        error_nodes = sum(1 for n in nodes if n.status == NodeStatus.ERROR)

        total_executors = sum(n.max_executors for n in nodes)
        used_executors = sum(n.current_executors for n in nodes)
        available_executors = total_executors - used_executors

        total_tests = sum(n.total_tests_executed for n in nodes)
        total_passed = sum(n.total_tests_passed for n in nodes)
        total_failed = sum(n.total_tests_failed for n in nodes)

        return {
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "busy_nodes": busy_nodes,
            "offline_nodes": offline_nodes,
            "error_nodes": error_nodes,
            "total_executors": total_executors,
            "used_executors": used_executors,
            "available_executors": available_executors,
            "total_tests_executed": total_tests,
            "total_tests_passed": total_passed,
            "total_tests_failed": total_failed,
            "pass_rate": round(total_passed / total_tests * 100, 2) if total_tests > 0 else 0
        }


# Global connection pool instance
connection_pool = NodeConnectionPool()
