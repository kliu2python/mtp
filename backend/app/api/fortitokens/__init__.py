"""FortiToken Warehouse API module."""

import logging
import os
import re
import shutil
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["FortiTokens"])

# Create directory for FortiToken PDFs
FORTITOKEN_DIR = Path(__file__).resolve().parent.parent / "uploads" / "fortitokens"
FORTITOKEN_DIR.mkdir(parents=True, exist_ok=True)

class FortiTokenCountResponse(BaseModel):
    """Response for FortiToken count."""
    count: int

class FortiTokenResponse(BaseModel):
    """Response for FortiToken random code."""
    code: Optional[str]

class RecycleCodeRequest(BaseModel):
    """Request for recycling a FortiToken activation code."""
    code: str

def _resolve_path(filename: str) -> Path:
    """Resolve a filename safely within the FortiToken directory."""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    candidate = Path(filename)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(status_code=400, detail="Invalid filename")

    full_path = (FORTITOKEN_DIR / candidate).resolve()
    try:
        full_path.relative_to(FORTITOKEN_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc

    return full_path

def extract_fortitoken_code(pdf_path: str) -> str:
    """
    Extract FortiToken activation code from PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        The extracted activation code or error message
    """
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        full_text = ""

        # Iterate through pages and extract text
        for page in doc:
            full_text += page.get_text()

        # Define the regex for the 20-digit Activation Code:
        # 4 chars - 4 chars - 4 chars - 4 chars - 4 chars
        code_pattern = r'[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}'

        # Search for the pattern
        match = re.search(code_pattern, full_text)

        if match:
            return match.group(0)
        else:
            return "Activation code not found."
    except Exception as e:
        logger.error(f"Error extracting code from {pdf_path}: {e}")
        return f"Error extracting code: {str(e)}"
    finally:
        # Close the document if it was opened
        try:
            doc.close()
        except:
            pass

def get_available_codes() -> List[tuple]:
    """
    Get all available activation codes from PDF files (excluding used files).

    Returns:
        List of tuples (filename, activation_code)
    """
    codes = []
    try:
        # Check if used directory exists
        used_dir = FORTITOKEN_DIR / "used"
        used_files = set()
        if used_dir.exists():
            # Get list of used files
            for item in used_dir.iterdir():
                if item.is_file():
                    used_files.add(item.name)

        for item in FORTITOKEN_DIR.iterdir():
            # Skip used directory and non-PDF files
            if item.name == "used" or not item.is_file() or not item.name.endswith('.pdf'):
                continue

            # Skip files that are already in used folder
            if item.name in used_files:
                continue

            # Check if we have extracted the code for this file
            code_file = item.with_suffix('.code')

            # If code file doesn't exist, extract and save it
            if not code_file.exists():
                activation_code = extract_fortitoken_code(str(item))
                # Save code to file if found
                if activation_code and activation_code != "Activation code not found." and not activation_code.startswith("Error"):
                    code_file.write_text(activation_code)
                    codes.append((item.name, activation_code))
            else:
                # Read existing code
                try:
                    activation_code = code_file.read_text().strip()
                    if activation_code:
                        codes.append((item.name, activation_code))
                except Exception as e:
                    logger.error(f"Failed to read code file {code_file}: {e}")
    except Exception as e:
        logger.error(f"Error getting available codes: {e}")

    return codes

@router.get("/count")
async def get_tokens_count() -> FortiTokenCountResponse:
    """Get count of available FortiToken activation codes."""
    codes = get_available_codes()
    return FortiTokenCountResponse(count=len(codes))

@router.post("/random")
async def get_random_token() -> FortiTokenResponse:
    """
    Get a random FortiToken activation code and move the associated files to used folder.

    Returns:
        Random activation code or None if no codes available
    """
    codes = get_available_codes()

    if not codes:
        return FortiTokenResponse(code=None)

    # Select random code
    filename, activation_code = random.choice(codes)

    # Move the PDF file and code file to used folder
    try:
        pdf_file = FORTITOKEN_DIR / filename
        code_file = pdf_file.with_suffix('.code')
        used_dir = FORTITOKEN_DIR / "used"

        # Create used directory if it doesn't exist
        used_dir.mkdir(exist_ok=True)

        # Move files to used directory
        if pdf_file.exists():
            pdf_file.rename(used_dir / filename)

        if code_file.exists():
            code_file.rename(used_dir / code_file.name)
    except Exception as e:
        logger.error(f"Error moving files for {filename}: {e}")
        # Even if moving fails, we still return the code

    return FortiTokenResponse(code=activation_code)

@router.post("/upload")
async def upload_tokens(files: List[UploadFile] = File(...)) -> dict:
    """Upload FortiToken PDF files."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    uploaded_files = []

    for upload in files:
        # Check if file is PDF
        if not upload.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {upload.filename} is not a PDF file")

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
            }
        )

    return {"message": "Files uploaded successfully", "files": uploaded_files}


@router.post("/recycle")
async def recycle_code(request: RecycleCodeRequest) -> dict:
    """
    Recycle a FortiToken activation code by adding it back to the available pool.

    Args:
        request: Contains the activation code to recycle

    Returns:
        Success message
    """
    code = request.code.strip()

    # Validate the code format (4 chars - 4 chars - 4 chars - 4 chars - 4 chars)
    code_pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
    if not re.match(code_pattern, code):
        raise HTTPException(status_code=400, detail="Invalid activation code format")

    # Create a simple text file with the code in the used directory
    used_dir = FORTITOKEN_DIR / "used"
    used_dir.mkdir(exist_ok=True)

    # Create a simple PDF-like file with the code
    recycled_filename = f"recycled_{code.replace('-', '')}.pdf"
    recycled_pdf_path = used_dir / recycled_filename

    # Create a simple text file that contains the code (simulating a PDF)
    recycled_pdf_path.write_text(f"Recycled FortiToken Activation Code: {code}\n")

    # Create the code file
    code_file_path = recycled_pdf_path.with_suffix('.code')
    code_file_path.write_text(code)

    # Move files from used to active directory
    active_pdf_path = FORTITOKEN_DIR / recycled_filename
    active_code_path = active_pdf_path.with_suffix('.code')

    try:
        # Move files back to active directory
        if recycled_pdf_path.exists():
            recycled_pdf_path.rename(active_pdf_path)

        if code_file_path.exists():
            code_file_path.rename(active_code_path)

        return {"message": f"Activation code {code} recycled successfully"}
    except Exception as e:
        logger.error(f"Error recycling code {code}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to recycle code: {str(e)}")