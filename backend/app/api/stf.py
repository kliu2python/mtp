"""
STF (Smartphone Test Farm) Integration API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.device import TestDevice, DeviceStatus, DeviceType
from app.services.stf_client import get_stf_client

logger = logging.getLogger(__name__)

router = APIRouter()


class STFSyncRequest(BaseModel):
    """Request to sync devices from STF"""
    auto_import: bool = True
    update_existing: bool = True


class STFDeviceReserveRequest(BaseModel):
    """Request to reserve a device through STF"""
    timeout_minutes: int = 15


@router.get("/devices")
async def list_stf_devices():
    """
    Get all devices from STF server

    Returns list of devices with their current status
    """
    try:
        stf_client = get_stf_client()
        devices = stf_client.get_all_devices()

        # Normalize devices to MTP format
        normalized_devices = [
            stf_client.normalize_device_data(device)
            for device in devices
        ]

        return {
            "total": len(normalized_devices),
            "devices": normalized_devices
        }
    except Exception as e:
        logger.error(f"Failed to fetch STF devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch STF devices: {str(e)}")


@router.post("/sync")
async def sync_stf_devices(
    request: STFSyncRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Sync devices from STF server to MTP database

    Args:
        request: Sync configuration
        db: Database session

    Returns:
        Sync results
    """
    try:
        stf_client = get_stf_client()
        stf_devices = stf_client.get_all_devices()

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for stf_device in stf_devices:
            device_data = stf_client.normalize_device_data(stf_device)
            device_id = device_data['device_id']

            if not device_id:
                logger.warning(f"Skipping device without serial: {stf_device.get('name')}")
                skipped_count += 1
                continue

            # Check if device exists
            existing_device = db.query(TestDevice).filter(
                TestDevice.device_id == device_id
            ).first()

            if existing_device:
                if request.update_existing:
                    # Update existing device
                    existing_device.name = device_data['name']
                    existing_device.platform = device_data['platform']
                    existing_device.os_version = device_data['os_version']
                    existing_device.status = DeviceStatus(device_data['status'])
                    existing_device.battery_level = device_data['battery_level']
                    existing_device.capabilities = device_data['capabilities']
                    existing_device.last_heartbeat = datetime.utcnow()
                    existing_device.updated_at = datetime.utcnow()

                    # Merge metadata
                    if existing_device.capabilities is None:
                        existing_device.capabilities = {}
                    existing_device.capabilities.update(device_data.get('metadata', {}))

                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                if request.auto_import:
                    # Create new device
                    new_device = TestDevice(
                        name=device_data['name'],
                        device_type=DeviceType(device_data['device_type']),
                        platform=device_data['platform'],
                        os_version=device_data['os_version'],
                        device_id=device_id,
                        connection_type=device_data['connection_type'],
                        status=DeviceStatus(device_data['status']),
                        battery_level=device_data['battery_level'],
                        capabilities=device_data.get('capabilities', {}),
                        tags=['stf', 'auto-imported'],
                        last_heartbeat=datetime.utcnow()
                    )

                    # Add metadata
                    if new_device.capabilities is None:
                        new_device.capabilities = {}
                    new_device.capabilities.update(device_data.get('metadata', {}))

                    db.add(new_device)
                    created_count += 1
                else:
                    skipped_count += 1

        db.commit()

        logger.info(f"STF sync completed: {created_count} created, {updated_count} updated, {skipped_count} skipped")

        return {
            "message": "STF devices synced successfully",
            "total_stf_devices": len(stf_devices),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count
        }
    except Exception as e:
        logger.error(f"Failed to sync STF devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync STF devices: {str(e)}")


@router.post("/devices/{device_id}/reserve")
async def reserve_stf_device(
    device_id: str,
    request: STFDeviceReserveRequest,
    db: Session = Depends(get_db)
):
    """
    Reserve a device through STF

    Args:
        device_id: Device ID (serial)
        request: Reservation parameters
        db: Database session

    Returns:
        Reservation result
    """
    try:
        # Get device from database
        device = db.query(TestDevice).filter(TestDevice.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found in MTP database")

        # Reserve through STF
        stf_client = get_stf_client()
        timeout_ms = request.timeout_minutes * 60 * 1000
        result = stf_client.add_device(device_id, timeout=timeout_ms)

        # Update device status in database
        device.status = DeviceStatus.BUSY
        device.last_heartbeat = datetime.utcnow()
        db.commit()

        logger.info(f"Device {device_id} reserved through STF")

        return {
            "message": "Device reserved successfully",
            "device_id": device_id,
            "timeout_minutes": request.timeout_minutes,
            "stf_response": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reserve device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reserve device: {str(e)}")


@router.post("/devices/{device_id}/release")
async def release_stf_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Release a device back to STF pool

    Args:
        device_id: Device ID (serial)
        db: Database session

    Returns:
        Release result
    """
    try:
        # Get device from database
        device = db.query(TestDevice).filter(TestDevice.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found in MTP database")

        # Release through STF
        stf_client = get_stf_client()
        result = stf_client.remove_device(device_id)

        # Update device status in database
        device.status = DeviceStatus.AVAILABLE
        device.current_test_id = None
        device.last_heartbeat = datetime.utcnow()
        db.commit()

        logger.info(f"Device {device_id} released back to STF pool")

        return {
            "message": "Device released successfully",
            "device_id": device_id,
            "stf_response": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to release device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to release device: {str(e)}")


@router.get("/devices/{device_id}")
async def get_stf_device_info(device_id: str):
    """
    Get detailed information about a device from STF

    Args:
        device_id: Device ID (serial)

    Returns:
        Device information
    """
    try:
        stf_client = get_stf_client()
        device_info = stf_client.get_device_info(device_id)

        if not device_info:
            raise HTTPException(status_code=404, detail="Device not found in STF")

        return {
            "device": stf_client.normalize_device_data(device_info),
            "raw_stf_data": device_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get device info for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device info: {str(e)}")


@router.get("/user/devices")
async def get_user_devices():
    """
    Get devices currently assigned to the STF user

    Returns:
        List of user's devices
    """
    try:
        stf_client = get_stf_client()
        devices = stf_client.get_user_devices()

        return {
            "total": len(devices),
            "devices": [stf_client.normalize_device_data(d) for d in devices]
        }
    except Exception as e:
        logger.error(f"Failed to get user devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user devices: {str(e)}")


@router.get("/stats")
async def get_stf_stats(db: Session = Depends(get_db)):
    """
    Get statistics about STF integration

    Returns:
        STF statistics
    """
    try:
        stf_client = get_stf_client()

        # Get STF devices
        all_stf_devices = stf_client.get_all_devices()
        user_devices = stf_client.get_user_devices()

        # Get synced devices from database
        stf_devices_in_db = db.query(TestDevice).filter(
            TestDevice.connection_type == 'stf'
        ).all()

        available_stf = sum(1 for d in all_stf_devices if d.get('ready', False) and not d.get('using', False))
        busy_stf = sum(1 for d in all_stf_devices if d.get('using', False))
        offline_stf = sum(1 for d in all_stf_devices if not d.get('present', False))

        return {
            "stf_total_devices": len(all_stf_devices),
            "stf_available": available_stf,
            "stf_busy": busy_stf,
            "stf_offline": offline_stf,
            "user_reserved_devices": len(user_devices),
            "synced_to_mtp": len(stf_devices_in_db),
            "not_synced": len(all_stf_devices) - len(stf_devices_in_db)
        }
    except Exception as e:
        logger.error(f"Failed to get STF stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get STF stats: {str(e)}")


@router.post("/test-connection")
async def test_stf_connection():
    """
    Test connection to STF server

    Returns:
        Connection test result
    """
    try:
        stf_client = get_stf_client()

        # Try to get user info
        user_info = stf_client.get_user_info()

        # Try to get devices
        devices = stf_client.get_all_devices()

        return {
            "success": True,
            "message": "Successfully connected to STF server",
            "user": user_info.get('user', {}),
            "total_devices": len(devices),
            "stf_url": stf_client.base_url
        }
    except Exception as e:
        logger.error(f"STF connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"STF connection failed: {str(e)}")
