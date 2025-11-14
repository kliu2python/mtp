"""
Device Management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.device import TestDevice, DeviceStatus, DeviceType
from app.services.device_manager import device_manager
from pydantic import BaseModel

router = APIRouter()


class DeviceCreate(BaseModel):
    name: str
    device_type: str
    platform: str
    os_version: str
    device_id: str
    connection_type: str = "usb"


@router.get("")
async def list_devices(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    os_version: Optional[str] = None,
    device_type: Optional[str] = None,
    available_only: bool = False,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all devices with optional filters"""
    query = db.query(TestDevice)

    if platform:
        query = query.filter(TestDevice.platform.ilike(f"%{platform}%"))
    if status:
        query = query.filter(TestDevice.status == status)
    if os_version:
        query = query.filter(TestDevice.os_version.ilike(f"%{os_version}%"))
    if device_type:
        query = query.filter(TestDevice.device_type == device_type)
    if location:
        query = query.filter(TestDevice.location.ilike(f"%{location}%"))
    if available_only:
        query = query.filter(TestDevice.status == DeviceStatus.AVAILABLE)

    devices = query.all()

    return {
        "total": len(devices),
        "devices": [device.to_dict() for device in devices]
    }


@router.get("/{device_id}")
async def get_device(device_id: str, db: Session = Depends(get_db)):
    """Get device by ID"""
    device = db.query(TestDevice).filter(TestDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device.to_dict()


@router.post("")
async def create_device(device_data: DeviceCreate, db: Session = Depends(get_db)):
    """Create a new device"""
    # Check if device_id already exists
    existing = db.query(TestDevice).filter(
        TestDevice.device_id == device_data.device_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device ID already exists")
    
    device = TestDevice(
        name=device_data.name,
        device_type=DeviceType(device_data.device_type),
        platform=device_data.platform,
        os_version=device_data.os_version,
        device_id=device_data.device_id,
        connection_type=device_data.connection_type,
        status=DeviceStatus.AVAILABLE
    )
    
    db.add(device)
    db.commit()
    db.refresh(device)
    
    return device.to_dict()


@router.delete("/{device_id}")
async def delete_device(device_id: str, db: Session = Depends(get_db)):
    """Delete device"""
    device = db.query(TestDevice).filter(TestDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.status == DeviceStatus.BUSY:
        raise HTTPException(status_code=400, detail="Cannot delete device in use")
    
    db.delete(device)
    db.commit()
    
    return {"message": "Device deleted successfully"}


@router.post("/refresh")
async def refresh_devices(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Refresh device list (discover new devices)"""
    try:
        # Discover devices in background
        devices = await device_manager.discover_devices()
        
        # Update database
        for device_info in devices:
            existing = db.query(TestDevice).filter(
                TestDevice.device_id == device_info["device_id"]
            ).first()
            
            if existing:
                # Update existing device
                existing.status = DeviceStatus.AVAILABLE
                existing.os_version = device_info.get("os_version", existing.os_version)
                existing.last_heartbeat = datetime.utcnow()
            else:
                # Create new device
                new_device = TestDevice(
                    name=device_info["name"],
                    device_type=DeviceType(device_info["device_type"]),
                    platform=device_info["platform"],
                    os_version=device_info["os_version"],
                    device_id=device_info["device_id"],
                    adb_id=device_info.get("adb_id"),
                    connection_type=device_info.get("connection_type", "usb"),
                    status=DeviceStatus.AVAILABLE
                )
                db.add(new_device)
        
        db.commit()
        
        return {
            "message": "Devices refreshed successfully",
            "discovered": len(devices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh devices: {str(e)}")


@router.post("/{device_id}/reserve")
async def reserve_device(
    device_id: str,
    test_id: str,
    db: Session = Depends(get_db)
):
    """Reserve device for testing"""
    device = db.query(TestDevice).filter(TestDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.status != DeviceStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Device not available")
    
    device.status = DeviceStatus.BUSY
    device.current_test_id = test_id
    device.last_heartbeat = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    return {
        "message": "Device reserved successfully",
        "device": device.to_dict()
    }


@router.post("/{device_id}/release")
async def release_device(device_id: str, db: Session = Depends(get_db)):
    """Release device after testing"""
    device = db.query(TestDevice).filter(TestDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.status = DeviceStatus.AVAILABLE
    device.current_test_id = None
    device.last_heartbeat = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    return {
        "message": "Device released successfully",
        "device": device.to_dict()
    }


@router.get("/{device_id}/health")
async def check_device_health(device_id: str, db: Session = Depends(get_db)):
    """Check device health status"""
    device = db.query(TestDevice).filter(TestDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        health = await device_manager.health_check(device)
        
        # Update device info
        device.battery_level = health.get("battery_level", device.battery_level)
        device.storage_free = health.get("storage_free", device.storage_free)
        device.last_heartbeat = datetime.utcnow()
        
        if health.get("online"):
            if device.status == DeviceStatus.OFFLINE:
                device.status = DeviceStatus.AVAILABLE
        else:
            device.status = DeviceStatus.OFFLINE
        
        db.commit()
        
        return health
    except Exception as e:
        return {
            "online": False,
            "status": "error",
            "error": str(e)
        }


@router.get("/stats/summary")
async def get_device_stats(db: Session = Depends(get_db)):
    """Get device statistics"""
    total = db.query(TestDevice).count()
    available = db.query(TestDevice).filter(
        TestDevice.status == DeviceStatus.AVAILABLE
    ).count()
    busy = db.query(TestDevice).filter(
        TestDevice.status == DeviceStatus.BUSY
    ).count()
    offline = db.query(TestDevice).filter(
        TestDevice.status == DeviceStatus.OFFLINE
    ).count()
    
    ios_count = db.query(TestDevice).filter(TestDevice.platform == "iOS").count()
    android_count = db.query(TestDevice).filter(TestDevice.platform == "Android").count()
    
    return {
        "total": total,
        "by_status": {
            "available": available,
            "busy": busy,
            "offline": offline
        },
        "by_platform": {
            "iOS": ios_count,
            "Android": android_count
        }
    }
