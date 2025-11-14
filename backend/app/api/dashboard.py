"""Dashboard API for monitoring Jenkins nodes and test execution"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta
import psutil

from app.core.database import get_db
from app.models.jenkins_node import JenkinsNode, NodeStatus
from app.services.test_executor import test_executor
from app.services.jenkins_pool import connection_pool

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Get comprehensive dashboard overview

    Returns:
        Dashboard data including:
        - Node statistics
        - Test execution status
        - System metrics
        - Recent activity
    """
    # Get all nodes
    nodes = db.query(JenkinsNode).all()

    # Calculate node statistics
    total_nodes = len(nodes)
    online_nodes = len([n for n in nodes if n.status == NodeStatus.ONLINE])
    busy_nodes = len([n for n in nodes if n.status == NodeStatus.BUSY])
    offline_nodes = len([n for n in nodes if n.status == NodeStatus.OFFLINE])
    error_nodes = len([n for n in nodes if n.status == NodeStatus.ERROR])

    # Calculate executor statistics
    total_executors = sum([n.max_executors for n in nodes])
    active_executors = sum([n.current_executors for n in nodes])
    available_executors = total_executors - active_executors

    # Get test execution statistics
    all_tasks = test_executor.get_all_tasks()
    running_tests = [t for t in all_tasks if t['status'] == 'running']
    queued_tests = [t for t in all_tasks if t['status'] == 'queued']
    completed_tests = [t for t in all_tasks if t['status'] == 'completed']
    failed_tests = [t for t in all_tasks if t['status'] == 'failed']

    # Calculate success rate
    total_finished = len(completed_tests) + len(failed_tests)
    success_rate = (len(completed_tests) / total_finished * 100) if total_finished > 0 else 0

    # Get node details with current tests
    node_details = []
    for node in nodes:
        # Get tests running on this node
        node_tests = [
            t for t in running_tests
            if t.get('node_id') == str(node.id)
        ]

        # Calculate pass rate
        pass_rate = round(node.total_tests_passed / node.total_tests_executed * 100, 2) if node.total_tests_executed > 0 else 0

        node_details.append({
            "id": str(node.id),
            "name": node.name,
            "host": node.host,
            "port": node.port,
            "status": node.status.value,
            "labels": node.labels,
            "current_executors": node.current_executors,
            "max_executors": node.max_executors,
            "utilization": (node.current_executors / node.max_executors * 100) if node.max_executors > 0 else 0,
            "running_tests": len(node_tests),
            "test_details": node_tests,
            "metrics": {
                "total_tests": node.total_tests_executed,
                "pass_rate": pass_rate,
                "avg_duration": node.average_test_duration,
                "cpu_usage": node.cpu_usage,
                "memory_usage": node.memory_usage,
                "disk_usage": node.disk_usage
            },
            "last_seen": node.last_seen.isoformat() if node.last_seen else None
        })

    # Get system metrics
    try:
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except Exception:
        system_metrics = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0
        }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": {
            "total": total_nodes,
            "online": online_nodes,
            "busy": busy_nodes,
            "offline": offline_nodes,
            "error": error_nodes
        },
        "executors": {
            "total": total_executors,
            "active": active_executors,
            "available": available_executors,
            "utilization": (active_executors / total_executors * 100) if total_executors > 0 else 0
        },
        "tests": {
            "running": len(running_tests),
            "queued": len(queued_tests),
            "completed_today": len(completed_tests),
            "failed_today": len(failed_tests),
            "success_rate": round(success_rate, 2),
            "total_today": len(all_tasks)
        },
        "node_details": node_details,
        "system_metrics": system_metrics,
        "pool_health": "healthy" if error_nodes == 0 and available_executors > 0 else "degraded"
    }


@router.get("/nodes/live")
async def get_nodes_live_status(db: Session = Depends(get_db)):
    """
    Get live status of all Jenkins nodes
    Optimized for frequent polling
    """
    nodes = db.query(JenkinsNode).all()
    all_tasks = test_executor.get_all_tasks()
    running_tests = [t for t in all_tasks if t['status'] == 'running']

    nodes_status = []
    for node in nodes:
        node_tests = [
            t for t in running_tests
            if t.get('node_id') == str(node.id)
        ]

        nodes_status.append({
            "id": str(node.id),
            "name": node.name,
            "status": node.status.value,
            "current_executors": node.current_executors,
            "max_executors": node.max_executors,
            "running_tests": len(node_tests),
            "cpu_usage": node.cpu_usage,
            "memory_usage": node.memory_usage
        })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": nodes_status
    }


@router.get("/tests/running")
async def get_running_tests():
    """Get all currently running tests with details"""
    all_tasks = test_executor.get_all_tasks()
    running_tests = [t for t in all_tasks if t['status'] == 'running']

    # Enrich with additional details
    enriched_tests = []
    for test in running_tests:
        enriched_tests.append({
            **test,
            "elapsed_time": (
                (datetime.fromisoformat(test['end_time']) if test.get('end_time') else datetime.utcnow()) -
                datetime.fromisoformat(test['start_time'])
            ).total_seconds() if test.get('start_time') else 0
        })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(enriched_tests),
        "tests": enriched_tests
    }


@router.get("/tests/queue")
async def get_queued_tests():
    """Get all queued tests waiting for execution"""
    all_tasks = test_executor.get_all_tasks()
    queued_tests = [t for t in all_tasks if t['status'] in ['queued', 'acquiring_node']]

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(queued_tests),
        "tests": queued_tests
    }


@router.get("/tests/recent")
async def get_recent_tests(limit: int = 20):
    """Get recent test executions (completed or failed)"""
    all_tasks = test_executor.get_all_tasks()
    finished_tests = [
        t for t in all_tasks
        if t['status'] in ['completed', 'failed']
    ]

    # Sort by end time, most recent first
    sorted_tests = sorted(
        finished_tests,
        key=lambda x: x.get('end_time', ''),
        reverse=True
    )[:limit]

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(sorted_tests),
        "tests": sorted_tests
    }


@router.get("/stats/hourly")
async def get_hourly_stats():
    """Get test execution statistics for the last 24 hours"""
    # This is a simplified version - in production you'd query from a time-series database
    all_tasks = test_executor.get_all_tasks()

    now = datetime.utcnow()
    hourly_stats = []

    for i in range(24):
        hour_start = now - timedelta(hours=i+1)
        hour_end = now - timedelta(hours=i)

        # Filter tests in this hour
        hour_tests = [
            t for t in all_tasks
            if t.get('start_time') and
               hour_start <= datetime.fromisoformat(t['start_time']) < hour_end
        ]

        completed = len([t for t in hour_tests if t['status'] == 'completed'])
        failed = len([t for t in hour_tests if t['status'] == 'failed'])

        hourly_stats.append({
            "hour": hour_start.strftime("%Y-%m-%d %H:00"),
            "total": len(hour_tests),
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / len(hour_tests) * 100) if hour_tests else 0
        })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "stats": list(reversed(hourly_stats))  # Oldest to newest
    }


@router.get("/alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """Get current system alerts and warnings"""
    alerts = []

    # Check nodes
    nodes = db.query(JenkinsNode).all()
    for node in nodes:
        # Offline nodes
        if node.status == NodeStatus.OFFLINE:
            alerts.append({
                "severity": "warning",
                "type": "node_offline",
                "message": f"Node '{node.name}' is offline",
                "node_id": str(node.id),
                "timestamp": node.last_seen.isoformat() if node.last_seen else None
            })

        # Error nodes
        if node.status == NodeStatus.ERROR:
            alerts.append({
                "severity": "error",
                "type": "node_error",
                "message": f"Node '{node.name}' is in error state",
                "node_id": str(node.id),
                "timestamp": datetime.utcnow().isoformat()
            })

        # High resource usage
        if node.cpu_usage and node.cpu_usage > 90:
            alerts.append({
                "severity": "warning",
                "type": "high_cpu",
                "message": f"Node '{node.name}' has high CPU usage ({node.cpu_usage:.1f}%)",
                "node_id": str(node.id),
                "value": node.cpu_usage
            })

        if node.memory_usage and node.memory_usage > 90:
            alerts.append({
                "severity": "warning",
                "type": "high_memory",
                "message": f"Node '{node.name}' has high memory usage ({node.memory_usage:.1f}%)",
                "node_id": str(node.id),
                "value": node.memory_usage
            })

        if node.disk_usage and node.disk_usage > 90:
            alerts.append({
                "severity": "error",
                "type": "high_disk",
                "message": f"Node '{node.name}' has high disk usage ({node.disk_usage:.1f}%)",
                "node_id": str(node.id),
                "value": node.disk_usage
            })

    # Check for long-running tests
    all_tasks = test_executor.get_all_tasks()
    for task in all_tasks:
        if task['status'] == 'running' and task.get('start_time'):
            start_time = datetime.fromisoformat(task['start_time'])
            elapsed = (datetime.utcnow() - start_time).total_seconds()

            # Alert if running more than 2 hours
            if elapsed > 7200:
                alerts.append({
                    "severity": "warning",
                    "type": "long_running_test",
                    "message": f"Test {task['task_id'][:8]} has been running for {elapsed/3600:.1f} hours",
                    "task_id": task['task_id'],
                    "elapsed_seconds": elapsed
                })

    # Check queue depth
    queued = len([t for t in all_tasks if t['status'] in ['queued', 'acquiring_node']])
    if queued > 10:
        alerts.append({
            "severity": "warning",
            "type": "high_queue_depth",
            "message": f"{queued} tests are waiting in queue",
            "queue_depth": queued
        })

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(alerts),
        "alerts": alerts
    }


@router.post("/nodes/{node_id}/action")
async def perform_node_action(
    node_id: str,
    action: str,
    db: Session = Depends(get_db)
):
    """
    Perform action on a node

    Actions: ping, restart, disable, enable
    """
    from uuid import UUID

    try:
        node_uuid = UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if action == "ping":
        # Ping the node
        result = connection_pool.ping_node(db, node_id)
        return {"action": "ping", "result": result}

    elif action == "disable":
        # Disable the node (set max_executors to 0)
        node.max_executors = 0
        node.status = NodeStatus.OFFLINE
        db.commit()
        return {"action": "disable", "message": f"Node {node.name} disabled"}

    elif action == "enable":
        # Enable the node
        if node.max_executors == 0:
            node.max_executors = 5  # Default
        node.status = NodeStatus.ONLINE
        db.commit()
        return {"action": "enable", "message": f"Node {node.name} enabled"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
