"""
Jenkins Slave Node API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from app.core.database import get_db
from app.models.jenkins_node import JenkinsNode, NodeStatus
from app.services.jenkins_pool import connection_pool
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class NodeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    max_executors: int = 2
    labels: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    max_executors: Optional[int] = None
    labels: Optional[List[str]] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class ConnectionTestRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    ssh_key: Optional[str] = None


@router.get("")
def list_nodes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all Jenkins slave nodes"""
    query = db.query(JenkinsNode)

    # Apply filters
    if status:
        try:
            status_enum = NodeStatus(status)
            query = query.filter(JenkinsNode.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if enabled is not None:
        query = query.filter(JenkinsNode.enabled == enabled)

    # Get total count
    total = query.count()

    # Apply pagination
    nodes = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "nodes": [node.to_dict() for node in nodes]
    }


@router.post("")
def create_node(node_data: NodeCreate, db: Session = Depends(get_db)):
    """Create a new Jenkins slave node"""
    # Check if name already exists
    existing = db.query(JenkinsNode).filter(JenkinsNode.name == node_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Node with name '{node_data.name}' already exists")

    # Test connection before creating
    test_result = connection_pool.test_ssh_connection(
        host=node_data.host,
        port=node_data.port,
        username=node_data.username,
        password=node_data.password,
        ssh_key=node_data.ssh_key
    )

    if not test_result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"SSH connection test failed: {test_result['message']}"
        )

    # Create node
    node = JenkinsNode(
        name=node_data.name,
        description=node_data.description,
        host=node_data.host,
        port=node_data.port,
        username=node_data.username,
        password=node_data.password,
        ssh_key=node_data.ssh_key,
        max_executors=node_data.max_executors,
        labels=node_data.labels or [],
        tags=node_data.tags or [],
        status=NodeStatus.ONLINE,
        last_ping_time=datetime.utcnow()
    )

    # Get initial system resources
    resources = connection_pool.get_system_resources(
        host=node_data.host,
        port=node_data.port,
        username=node_data.username,
        password=node_data.password,
        ssh_key=node_data.ssh_key
    )
    node.cpu_usage = resources["cpu_usage"]
    node.memory_usage = resources["memory_usage"]
    node.disk_usage = resources["disk_usage"]

    db.add(node)
    db.commit()
    db.refresh(node)

    logger.info(f"Created Jenkins node: {node.name} ({node.host}:{node.port})")
    return node.to_dict()


@router.get("/{node_id}")
def get_node(node_id: str, db: Session = Depends(get_db)):
    """Get a specific Jenkins slave node"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return node.to_dict()


@router.put("/{node_id}")
def update_node(node_id: str, node_data: NodeUpdate, db: Session = Depends(get_db)):
    """Update a Jenkins slave node"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Update fields
    update_data = node_data.dict(exclude_unset=True)

    # If connection details changed, test the connection
    if any(key in update_data for key in ["host", "port", "username", "password", "ssh_key"]):
        host = update_data.get("host", node.host)
        port = update_data.get("port", node.port)
        username = update_data.get("username", node.username)
        password = update_data.get("password", node.password)
        ssh_key = update_data.get("ssh_key", node.ssh_key)

        test_result = connection_pool.test_ssh_connection(
            host=host,
            port=port,
            username=username,
            password=password,
            ssh_key=ssh_key
        )

        if not test_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"SSH connection test failed: {test_result['message']}"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(node, key, value)

    node.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(node)

    logger.info(f"Updated Jenkins node: {node.name}")
    return node.to_dict()


@router.delete("/{node_id}")
def delete_node(node_id: str, db: Session = Depends(get_db)):
    """Delete a Jenkins slave node"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Check if node is currently in use
    if node.current_executors > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete node with active executors ({node.current_executors} running)"
        )

    node_name = node.name
    db.delete(node)
    db.commit()

    logger.info(f"Deleted Jenkins node: {node_name}")
    return {"message": f"Node '{node_name}' deleted successfully"}


@router.post("/test-connection")
def test_connection(request: ConnectionTestRequest):
    """Test SSH connection to a node without creating it"""
    result = connection_pool.test_ssh_connection(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password,
        ssh_key=request.ssh_key
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Also get system resources
    resources = connection_pool.get_system_resources(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password,
        ssh_key=request.ssh_key
    )

    return {
        **result,
        **resources
    }


@router.post("/{node_id}/ping")
def ping_node(node_id: str, db: Session = Depends(get_db)):
    """Ping a node to check its status"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Test connection
    result = connection_pool.test_ssh_connection(
        host=node.host,
        port=node.port,
        username=node.username,
        password=node.password,
        ssh_key=node.ssh_key
    )

    # Update node status
    if result["success"]:
        if node.current_executors == 0:
            node.status = NodeStatus.ONLINE
        node.last_ping_time = datetime.utcnow()
        node.last_error = None

        # Get system resources
        resources = connection_pool.get_system_resources(
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
    db.refresh(node)

    return {
        **result,
        "node": node.to_dict()
    }


@router.post("/{node_id}/enable")
def enable_node(node_id: str, db: Session = Depends(get_db)):
    """Enable a node"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.enabled = True
    db.commit()
    db.refresh(node)

    logger.info(f"Enabled Jenkins node: {node.name}")
    return node.to_dict()


@router.post("/{node_id}/disable")
def disable_node(node_id: str, db: Session = Depends(get_db)):
    """Disable a node"""
    try:
        node_uuid = uuid.UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")

    node = db.get(JenkinsNode, node_uuid)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.enabled = False
    node.status = NodeStatus.OFFLINE
    db.commit()
    db.refresh(node)

    logger.info(f"Disabled Jenkins node: {node.name}")
    return node.to_dict()


@router.get("/pool/stats")
def get_pool_stats(db: Session = Depends(get_db)):
    """Get connection pool statistics"""
    stats = connection_pool.get_pool_stats(db)
    return stats


@router.post("/pool/health-check")
async def health_check_all(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Perform health check on all nodes"""
    # Run health check in background
    await connection_pool.health_check_all_nodes(db)

    return {"message": "Health check completed"}
