"""
Virtual Machine API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import contextlib

import asyncssh

from app.core.database import get_db
from app.models.vm import VirtualMachine, VMStatus, VMPlatform, TestRecord
from app.services.docker_service import docker_service
from pydantic import BaseModel

router = APIRouter()


class VMCreate(BaseModel):
    name: str
    platform: str
    version: str
    test_priority: int = 3
    ip_address: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None


class VMUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    version: Optional[str] = None
    ip_address: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    status: Optional[str] = None
    test_priority: Optional[int] = None
    tags: Optional[List[str]] = None


@router.get("")
async def list_vms(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all VMs with optional filters"""
    query = db.query(VirtualMachine)
    
    if platform:
        query = query.filter(VirtualMachine.platform == platform)
    if status:
        query = query.filter(VirtualMachine.status == status)
    
    vms = query.offset(skip).limit(limit).all()
    
    return {
        "total": query.count(),
        "vms": [vm.to_dict() for vm in vms]
    }


@router.get("/{vm_id}")
async def get_vm(vm_id: str, db: Session = Depends(get_db)):
    """Get VM by ID"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    return vm.to_dict()


@router.post("")
async def create_vm(vm_data: VMCreate, db: Session = Depends(get_db)):
    """Create a new VM"""
    # Check if name already exists
    existing = db.query(VirtualMachine).filter(VirtualMachine.name == vm_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="VM name already exists")
    
    vm = VirtualMachine(
        name=vm_data.name,
        platform=VMPlatform(vm_data.platform),
        version=vm_data.version,
        test_priority=vm_data.test_priority,
        ip_address=vm_data.ip_address,
        ssh_username=vm_data.ssh_username,
        ssh_password=vm_data.ssh_password,
        status=VMStatus.STOPPED
    )
    
    db.add(vm)
    db.commit()
    db.refresh(vm)
    
    return vm.to_dict()


@router.put("/{vm_id}")
async def update_vm(vm_id: str, vm_data: VMUpdate, db: Session = Depends(get_db)):
    """Update VM"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    if vm_data.name is not None:
        vm.name = vm_data.name
    if vm_data.platform is not None:
        vm.platform = VMPlatform(vm_data.platform)
    if vm_data.version is not None:
        vm.version = vm_data.version
    if vm_data.ip_address is not None:
        vm.ip_address = vm_data.ip_address
    if vm_data.ssh_username is not None:
        vm.ssh_username = vm_data.ssh_username
    if vm_data.ssh_password is not None:
        vm.ssh_password = vm_data.ssh_password
    if vm_data.status:
        vm.status = VMStatus(vm_data.status)
    if vm_data.test_priority is not None:
        vm.test_priority = vm_data.test_priority
    if vm_data.tags is not None:
        vm.tags = vm_data.tags
    
    vm.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vm)
    
    return vm.to_dict()


@router.delete("/{vm_id}")
async def delete_vm(vm_id: str, db: Session = Depends(get_db)):
    """Delete VM"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    # Stop container if running
    if vm.docker_container_id:
        try:
            await docker_service.stop_container(vm.docker_container_id)
        except:
            pass
    
    db.delete(vm)
    db.commit()
    
    return {"message": "VM deleted successfully"}


@router.post("/{vm_id}/start")
async def start_vm(vm_id: str, db: Session = Depends(get_db)):
    """Start VM (create Docker container)"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    if vm.status == VMStatus.RUNNING:
        return {"message": "VM already running", "vm": vm.to_dict()}
    
    try:
        # Create and start container
        container_id = await docker_service.start_vm(vm)
        
        vm.docker_container_id = container_id
        vm.status = VMStatus.RUNNING
        vm.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(vm)
        
        return {"message": "VM started successfully", "vm": vm.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start VM: {str(e)}")


@router.post("/{vm_id}/stop")
async def stop_vm(vm_id: str, db: Session = Depends(get_db)):
    """Stop VM (stop Docker container)"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    if vm.status == VMStatus.STOPPED:
        return {"message": "VM already stopped", "vm": vm.to_dict()}
    
    try:
        if vm.docker_container_id:
            await docker_service.stop_container(vm.docker_container_id)
        
        vm.status = VMStatus.STOPPED
        vm.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(vm)
        
        return {"message": "VM stopped successfully", "vm": vm.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop VM: {str(e)}")


@router.get("/{vm_id}/logs")
async def get_vm_logs(
    vm_id: str,
    tail: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get VM logs"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    if not vm.docker_container_id:
        return {"logs": []}
    
    try:
        logs = await docker_service.get_container_logs(vm.docker_container_id, tail=tail)
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@router.get("/{vm_id}/metrics")
async def get_vm_metrics(vm_id: str, db: Session = Depends(get_db)):
    """Get VM resource metrics"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    if not vm.docker_container_id or vm.status != VMStatus.RUNNING:
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0
        }
    
    try:
        metrics = await docker_service.get_container_stats(vm.docker_container_id)
        
        # Update VM metrics
        vm.cpu_usage = metrics.get("cpu_percent", 0)
        vm.memory_usage = metrics.get("memory_percent", 0)
        vm.disk_usage = metrics.get("disk_percent", 0)
        db.commit()

        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.websocket("/{vm_id}/ssh")
async def ssh_console(websocket: WebSocket, vm_id: str, db: Session = Depends(get_db)):
    """Proxy SSH session for the given VM over WebSocket."""
    await websocket.accept()

    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        await websocket.send_text("Error: VM not found.")
        await websocket.close(code=1008)
        return

    if not vm.ip_address or not vm.ssh_username:
        await websocket.send_text("Error: SSH connection details are incomplete for this VM.")
        await websocket.close(code=1008)
        return

    ssh_kwargs = {
        "host": vm.ip_address,
        "username": vm.ssh_username,
        "known_hosts": None,
    }

    if vm.ssh_password:
        ssh_kwargs["password"] = vm.ssh_password

    try:
        connection = await asyncssh.connect(**ssh_kwargs)
        process = await connection.create_process(term_type="xterm")
    except Exception as exc:
        await websocket.send_text(f"Error: Unable to establish SSH session ({exc}).")
        await websocket.close(code=1011)
        return

    await websocket.send_text(f"Connected to {vm.ip_address} as {vm.ssh_username}\r\n")

    async def forward_ssh_output(stream):
        try:
            while True:
                data = await stream.read(1024)
                if not data:
                    break
                await websocket.send_text(data)
        except Exception:
            pass

    async def forward_websocket_input():
        try:
            while True:
                data = await websocket.receive_text()
                process.stdin.write(data)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            try:
                process.stdin.write_eof()
            except Exception:
                pass

    tasks = [
        asyncio.create_task(forward_ssh_output(process.stdout)),
        asyncio.create_task(forward_ssh_output(process.stderr)),
        asyncio.create_task(forward_websocket_input()),
    ]

    done: set = set()
    pending: set = set()
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    finally:
        for task in done:
            with contextlib.suppress(Exception):
                await task
        process.close()
        connection.close()
        with contextlib.suppress(Exception):
            await process.wait_closed()
        with contextlib.suppress(Exception):
            await connection.wait_closed()
        with contextlib.suppress(Exception):
            await websocket.close()

@router.get("/{vm_id}/tests")
async def get_vm_test_records(
    vm_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get test records for a VM"""
    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    records = db.query(TestRecord).filter(
        TestRecord.vm_id == vm_id
    ).order_by(
        TestRecord.executed_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "total": db.query(TestRecord).filter(TestRecord.vm_id == vm_id).count(),
        "records": [record.to_dict() for record in records]
    }


@router.get("/stats/summary")
async def get_stats_summary(db: Session = Depends(get_db)):
    """Get overall statistics"""
    total_vms = db.query(VirtualMachine).count()
    running_vms = db.query(VirtualMachine).filter(
        VirtualMachine.status == VMStatus.RUNNING
    ).count()
    testing_vms = db.query(VirtualMachine).filter(
        VirtualMachine.status == VMStatus.TESTING
    ).count()
    
    # Platform distribution
    fortigate_count = db.query(VirtualMachine).filter(
        VirtualMachine.platform == VMPlatform.FORTIGATE
    ).count()
    fortiauthenticator_count = db.query(VirtualMachine).filter(
        VirtualMachine.platform == VMPlatform.FORTIAUTHENTICATOR
    ).count()
    
    # Test statistics (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_tests = db.query(TestRecord).filter(
        TestRecord.executed_at >= yesterday
    ).all()
    
    total_tests = len(recent_tests)
    passed_tests = sum(1 for t in recent_tests if t.status == "passed")
    failed_tests = sum(1 for t in recent_tests if t.status == "failed")
    
    return {
        "vms": {
            "total": total_vms,
            "running": running_vms,
            "testing": testing_vms,
            "by_platform": {
                "FortiGate": fortigate_count,
                "FortiAuthenticator": fortiauthenticator_count
            }
        },
        "tests_24h": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": round(passed_tests / total_tests * 100, 2) if total_tests > 0 else 0
        }
    }
