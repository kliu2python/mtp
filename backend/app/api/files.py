"""
File Management API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path

router = APIRouter()

UPLOAD_DIR = Path("/test-files")


@router.get("/browse")
async def browse_files(path: str = "/"):
    """Browse file system"""
    try:
        full_path = UPLOAD_DIR / path.lstrip("/")
        if not full_path.exists():
            return {"items": []}
        
        items = []
        for item in full_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str(item.relative_to(UPLOAD_DIR)),
                "size": item.stat().st_size if item.is_file() else 0
            })
        
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), path: str = "/"):
    """Upload a file"""
    try:
        full_path = UPLOAD_DIR / path.lstrip("/")
        full_path.mkdir(parents=True, exist_ok=True)
        
        file_path = full_path / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "message": "File uploaded successfully",
            "path": str(file_path.relative_to(UPLOAD_DIR)),
            "size": file_path.stat().st_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download a file"""
    full_path = UPLOAD_DIR / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(full_path)
