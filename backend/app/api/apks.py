"""
APK/IPA file management API
"""
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.apk_file import ApkFile, AppPlatform
from app.services.apk_parser import parse_app_metadata, get_platform_from_extension

logger = logging.getLogger(__name__)

router = APIRouter()

# APK storage directory
APK_UPLOAD_DIR = Path(os.getenv("APK_UPLOAD_DIR", "/home/user/mtp/backend/app/uploads/apks"))
APK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ApkFileCreate(BaseModel):
    """Schema for creating APK file record"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    uploaded_by: Optional[str] = None


class ApkFileUpdate(BaseModel):
    """Schema for updating APK file record"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_apk_files(
    platform: Optional[str] = Query(None, description="Filter by platform (android/ios)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    package_name: Optional[str] = Query(None, description="Filter by package name"),
    search: Optional[str] = Query(None, description="Search in display name or package name"),
    db: Session = Depends(get_db)
):
    """
    List all APK/IPA files with optional filters
    """
    query = db.query(ApkFile)

    # Apply filters
    if platform:
        try:
            platform_enum = AppPlatform(platform.lower())
            query = query.filter(ApkFile.platform == platform_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")

    if is_active is not None:
        query = query.filter(ApkFile.is_active == is_active)

    if package_name:
        query = query.filter(ApkFile.package_name.ilike(f"%{package_name}%"))

    if search:
        query = query.filter(
            (ApkFile.display_name.ilike(f"%{search}%")) |
            (ApkFile.package_name.ilike(f"%{search}%")) |
            (ApkFile.filename.ilike(f"%{search}%"))
        )

    # Order by created_at descending (newest first)
    apk_files = query.order_by(ApkFile.created_at.desc()).all()

    return {"apk_files": [apk.to_dict() for apk in apk_files]}


@router.get("/{apk_id}")
async def get_apk_file(apk_id: str, db: Session = Depends(get_db)):
    """
    Get details of a specific APK/IPA file
    """
    apk_file = db.query(ApkFile).filter(ApkFile.id == apk_id).first()
    if not apk_file:
        raise HTTPException(status_code=404, detail="APK file not found")

    return apk_file.to_dict()


@router.post("/upload")
async def upload_apk_file(
    file: UploadFile = File(...),
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    uploaded_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload a new APK/IPA file and parse its metadata
    """
    # Validate file extension
    platform = get_platform_from_extension(file.filename)
    if not platform:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .apk and .ipa files are supported"
        )

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = APK_UPLOAD_DIR / safe_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Parse metadata
    try:
        metadata = parse_app_metadata(str(file_path), platform)
    except Exception as e:
        logger.error(f"Failed to parse metadata: {e}")
        metadata = {"file_size": os.path.getsize(file_path), "platform": platform}

    # Create database record
    apk_file = ApkFile(
        filename=file.filename,
        display_name=display_name or file.filename,
        platform=AppPlatform(platform),
        file_path=str(file_path),
        file_size=metadata.get("file_size", 0),
        file_hash=metadata.get("file_hash"),
        package_name=metadata.get("package_name"),
        version_name=metadata.get("version_name"),
        version_code=metadata.get("version_code"),
        min_sdk_version=metadata.get("min_sdk_version"),
        target_sdk_version=metadata.get("target_sdk_version"),
        bundle_id=metadata.get("bundle_id"),
        description=description,
        tags=tags.split(",") if tags else [],
        app_metadata=metadata,
        uploaded_by=uploaded_by,
        is_active=True
    )

    db.add(apk_file)
    db.commit()
    db.refresh(apk_file)

    logger.info(f"Uploaded APK file: {file.filename} (ID: {apk_file.id})")

    return {
        "message": "APK file uploaded successfully",
        "apk_file": apk_file.to_dict()
    }


@router.put("/{apk_id}")
async def update_apk_file(
    apk_id: str,
    update_data: ApkFileUpdate,
    db: Session = Depends(get_db)
):
    """
    Update APK/IPA file metadata
    """
    apk_file = db.query(ApkFile).filter(ApkFile.id == apk_id).first()
    if not apk_file:
        raise HTTPException(status_code=404, detail="APK file not found")

    # Update fields
    if update_data.display_name is not None:
        apk_file.display_name = update_data.display_name
    if update_data.description is not None:
        apk_file.description = update_data.description
    if update_data.tags is not None:
        apk_file.tags = update_data.tags
    if update_data.is_active is not None:
        apk_file.is_active = update_data.is_active

    apk_file.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(apk_file)

    return {
        "message": "APK file updated successfully",
        "apk_file": apk_file.to_dict()
    }


@router.delete("/{apk_id}")
async def delete_apk_file(apk_id: str, db: Session = Depends(get_db)):
    """
    Delete an APK/IPA file (soft delete by default)
    """
    apk_file = db.query(ApkFile).filter(ApkFile.id == apk_id).first()
    if not apk_file:
        raise HTTPException(status_code=404, detail="APK file not found")

    # Soft delete (mark as inactive)
    apk_file.is_active = False
    apk_file.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "APK file deleted successfully"}


@router.delete("/{apk_id}/permanent")
async def permanently_delete_apk_file(apk_id: str, db: Session = Depends(get_db)):
    """
    Permanently delete an APK/IPA file from database and filesystem
    """
    apk_file = db.query(ApkFile).filter(ApkFile.id == apk_id).first()
    if not apk_file:
        raise HTTPException(status_code=404, detail="APK file not found")

    # Delete physical file
    try:
        file_path = Path(apk_file.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")

    # Delete database record
    db.delete(apk_file)
    db.commit()

    return {"message": "APK file permanently deleted"}


@router.get("/stats/summary")
async def get_apk_stats(db: Session = Depends(get_db)):
    """
    Get statistics about APK files
    """
    total_count = db.query(ApkFile).count()
    active_count = db.query(ApkFile).filter(ApkFile.is_active == True).count()
    android_count = db.query(ApkFile).filter(ApkFile.platform == AppPlatform.ANDROID).count()
    ios_count = db.query(ApkFile).filter(ApkFile.platform == AppPlatform.IOS).count()

    # Total storage size
    all_apks = db.query(ApkFile).all()
    total_size = sum(apk.file_size for apk in all_apks)

    return {
        "total_count": total_count,
        "active_count": active_count,
        "inactive_count": total_count - active_count,
        "android_count": android_count,
        "ios_count": ios_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }
