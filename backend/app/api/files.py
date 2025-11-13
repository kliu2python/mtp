"""File management API."""

from __future__ import annotations

import logging
import os
import shutil
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.qr_generator import generate_qr_data_url

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


def _initialize_upload_dir() -> Path:
    """Determine and prepare the upload directory."""

    configured_path = Path(os.getenv("UPLOAD_FOLDER", settings.UPLOAD_DIR)).expanduser()

    try:
        configured_path.mkdir(parents=True, exist_ok=True)
        if not os.access(configured_path, os.W_OK):
            raise PermissionError(f"Upload directory '{configured_path}' is not writable")
        return configured_path
    except Exception as exc:  # pragma: no cover - fallback path is best-effort
        logger.warning(
            "Unable to access configured upload folder '%s', falling back to default '%s'.",
            configured_path,
            DEFAULT_UPLOAD_DIR,
            exc_info=exc,
        )
        DEFAULT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_UPLOAD_DIR


UPLOAD_DIR = _initialize_upload_dir()


def _resolve_path(filename: str) -> Path:
    """Resolve a filename safely within the upload directory."""

    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    candidate = Path(filename)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(status_code=400, detail="Invalid filename")

    full_path = (UPLOAD_DIR / candidate).resolve()
    try:
        full_path.relative_to(UPLOAD_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc

    return full_path


def _build_file_listing() -> List[dict]:
    """Return details for files in the upload directory."""

    details: List[dict] = []
    try:
        for item in sorted(UPLOAD_DIR.iterdir()):
            if not item.is_file():
                continue

            stats = item.stat()
            details.append(
                {
                    "name": item.name,
                    "size": stats.st_size,
                    "uploadDate": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    "path": f"/uploads/{urllib.parse.quote(item.name)}",
                }
            )
    except FileNotFoundError:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - runtime failure path
        raise HTTPException(status_code=500, detail="Failed to read files") from exc

    return details


@router.get("/")
async def list_files() -> List[dict]:
    """List uploaded files."""

    return _build_file_listing()


@router.get("/browse")
async def browse_files() -> dict:
    """Legacy endpoint returning items under an `items` key."""

    return {"items": _build_file_listing()}


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> dict:
    """Upload one or more files."""

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    uploaded_files = []

    for upload in files:
        destination = _resolve_path(upload.filename)
        destination.parent.mkdir(parents=True, exist_ok=True)

        upload.file.seek(0)
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        stats = destination.stat()
        uploaded_files.append(
            {
                "name": destination.name,
                "size": stats.st_size,
                "path": f"/uploads/{urllib.parse.quote(destination.name)}",
            }
        )

    return {"message": "Files uploaded successfully", "files": uploaded_files}


@router.get("/download/{filename:path}")
async def download_file(filename: str):
    """Download a file."""

    file_path = _resolve_path(filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=file_path.name)


@router.get("/qr/{filename:path}")
async def generate_qr_code(filename: str, request: Request) -> dict:
    """Generate a QR code for the download URL of a file."""

    file_path = _resolve_path(filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    base_url = str(request.base_url).rstrip("/")
    download_url = f"{base_url}/uploads/{urllib.parse.quote(file_path.name)}"

    try:
        qr_data_url = generate_qr_data_url(
            download_url,
            error_correction="M",
            module_scale=8,
            margin=2,
        )
    except ValueError as exc:
        message = str(exc)
        if "too long" in message.lower():
            raise HTTPException(status_code=422, detail="Download link is too long to encode as a QR code") from exc
        raise HTTPException(status_code=500, detail="Unable to generate QR code") from exc

    return {
        "filename": file_path.name,
        "downloadUrl": download_url,
        "qrDataUrl": qr_data_url,
    }


@router.get("/file/{filename:path}")
async def read_file(filename: str) -> dict:
    """Read the contents of a text file."""

    file_path = _resolve_path(filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="File is not a UTF-8 encoded text file") from exc
    except OSError as exc:  # pragma: no cover - runtime failure path
        raise HTTPException(status_code=500, detail="Failed to read file") from exc

    return {"content": content}


class UpdateFileRequest(BaseModel):
    """Payload for file updates."""

    newName: Optional[str] = None
    content: Optional[str] = None


@router.put("/file/{filename:path}")
async def update_file(filename: str, payload: UpdateFileRequest) -> dict:
    """Update file contents or rename a file."""

    file_path = _resolve_path(filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        if payload.content is not None:
            file_path.write_text(payload.content, encoding="utf-8")

        updated_path = file_path
        if payload.newName and payload.newName != file_path.name:
            new_path = _resolve_path(payload.newName)
            file_path.rename(new_path)
            updated_path = new_path
    except OSError as exc:  # pragma: no cover - runtime failure path
        raise HTTPException(status_code=500, detail="Failed to update file") from exc

    return {"message": "File updated successfully", "filename": updated_path.name}


@router.delete("/file/{filename:path}")
async def delete_file(filename: str) -> dict:
    """Delete a file."""

    file_path = _resolve_path(filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.unlink()
    except OSError as exc:  # pragma: no cover - runtime failure path
        raise HTTPException(status_code=500, detail="Failed to delete file") from exc

    return {"message": "File deleted successfully"}
