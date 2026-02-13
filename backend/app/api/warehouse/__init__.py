"""
Unified Warehouse API module.
Combines functionality for FortiGate, FortiAuthenticator, and FortiToken codes.
"""
import logging
import shutil
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.license import License
from app.models.fortitoken import FortiToken
from app.services.warehouse_auth_service import warehouse_auth_service
# Define directories for license and fortitoken PDFs
from pathlib import Path
LICENSE_DIR = Path(__file__).resolve().parent.parent / "uploads" / "licenses"
FORTITOKEN_DIR = Path(__file__).resolve().parent.parent / "uploads" / "fortitokens"

# Create directories if they don't exist
LICENSE_DIR.mkdir(parents=True, exist_ok=True)
FORTITOKEN_DIR.mkdir(parents=True, exist_ok=True)

import re
import fitz  # PyMuPDF
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def verify_warehouse_access(authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Dependency to verify warehouse access using OTP authentication.

    Args:
        authorization: Authorization header containing email in format "Bearer user@fortinet.com"
        db: Database session

    Returns:
        Email address if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )

    # Parse authorization header (expected format: "Bearer user@fortinet.com")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer user@fortinet.com"
        )

    email = authorization[7:].strip()  # Remove "Bearer " prefix

    # Validate email format
    if not email or "@" not in email:
        raise HTTPException(
            status_code=401,
            detail="Invalid email format in authorization header"
        )

    # Check if OTP is verified for this email
    is_verified = warehouse_auth_service.is_otp_verified(db, email)

    if not is_verified:
        raise HTTPException(
            status_code=401,
            detail="Warehouse access not authorized. Please generate and verify OTP first."
        )

    return email

def extract_registration_code(pdf_path: str) -> tuple:
    """
    Extract registration code, license type, and size information from FortiGate/FortiAuthenticator/FortiIdentity Cloud license PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Tuple of (registration_code, license_type, size_info) or error message
    """
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        full_text = ""

        # Iterate through pages and extract text
        for page in doc:
            full_text += page.get_text()

        # First, try to find the Contract Registration Code pattern (12 alphanumeric characters)
        # Looking for pattern like 4456UL989056 (mix of digits and letters)
        # This pattern ensures we have both letters and digits to avoid matching regular words
        contract_code_pattern = r'[A-Z0-9]{12}'

        # Find ALL matches instead of just the first one
        all_matches = re.findall(contract_code_pattern, full_text)

        # Look for the valid one (contains both letters and digits)
        valid_contract_code = None
        for match in all_matches:
            has_letters = any(c.isalpha() for c in match)
            has_digits = any(c.isdigit() for c in match)
            if has_letters and has_digits:
                valid_contract_code = match
                break

        registration_code = "Registration code not found."
        if valid_contract_code:
            registration_code = valid_contract_code
        else:
            # If no contract code found, try the traditional format
            # Define the regex for the registration code:
            # Format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXXX (5-5-5-5-6 pattern)
            code_pattern = r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{6}'

            # Search for the pattern
            match = re.search(code_pattern, full_text)

            if match:
                registration_code = match.group(0)

        # Determine license type based on keywords in the text
        license_type = "Unknown"
        size_info = None
        full_text_lower = full_text.lower()

        if 'fortigate' in full_text_lower or 'fg-' in full_text_lower or 'fgvm' in full_text_lower:
            license_type = "FortiGate"
        elif 'fortiauthenticator' in full_text_lower or 'fac-' in full_text_lower or 'facvm' in full_text_lower:
            license_type = "FortiAuthenticator"
        elif 'fortiidentity cloud' in full_text_lower or 'idcld' in full_text_lower:
            # Specifically identify FortiIdentity Cloud codes
            license_type = "FortiIdentity Cloud"
            # Extract size information for FortiIdentity Cloud codes
            # Looking for pattern like "Units of Contract :10000"
            size_pattern = r'units of contract\s*:\s*(\d+)'
            size_match = re.search(size_pattern, full_text_lower)
            if size_match:
                size_info = size_match.group(1)
        elif valid_contract_code and 'contract' in full_text_lower and 'registration' in full_text_lower:
            # If it's a contract registration code, we can classify it as Contract type
            # For now, we'll still use Unknown to maintain compatibility, but we could create a specific type
            license_type = "Unknown"

        return (registration_code, license_type, size_info)
    except Exception as e:
        # Log the error (would need proper logger setup)
        return (f"Error extracting code: {str(e)}", "Unknown", None)
    finally:
        # Close the document if it was opened
        try:
            doc.close()
        except:
            pass

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
        return f"Error extracting code: {str(e)}"
    finally:
        # Close the document if it was opened
        try:
            doc.close()
        except:
            pass

logger = logging.getLogger(__name__)

# Import the warehouse auth router
from app.api.warehouse_auth import router as warehouse_auth_router

router = APIRouter(tags=["Warehouse"])

# Include the warehouse auth router without any prefix
router.include_router(warehouse_auth_router, tags=["Warehouse Authentication"])

# Response models
class WarehouseCountResponse(BaseModel):
    """Response for warehouse counts by type."""
    fortigate: int
    fortiauthenticator: int
    fortitoken: int
    fortidentitycloud: int
    total: int

class WarehouseCodeResponse(BaseModel):
    """Response for warehouse code retrieval."""
    code: Optional[str]
    filename: Optional[str]
    code_type: Optional[str]
    size: Optional[str] = None

class RecycleCodeRequest(BaseModel):
    """Request for recycling any type of code."""
    code: str

class UploadResponse(BaseModel):
    """Response for upload operations."""
    message: str
    files: List[dict]

def _resolve_license_path(filename: str) -> Path:
    """Resolve a filename safely within the license directory."""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    candidate = Path(filename)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(status_code=400, detail="Invalid filename")

    full_path = (LICENSE_DIR / candidate).resolve()
    try:
        full_path.relative_to(LICENSE_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc

    return full_path

def _resolve_fortitoken_path(filename: str) -> Path:
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

@router.get("/count")
async def get_warehouse_counts(db: Session = Depends(get_db)) -> WarehouseCountResponse:
    """
    Get counts of available codes for all types.

    Returns:
        Counts for each code type and total
    """
    # Count available licenses by type
    fortigate_count = db.query(License).filter(
        License.status == "available",
        License.license_type == "FortiGate"
    ).count()

    fortiauthenticator_count = db.query(License).filter(
        License.status == "available",
        License.license_type == "FortiAuthenticator"
    ).count()

    fortidentitycloud_count = db.query(License).filter(
        License.status == "available",
        License.license_type == "FortiIdentity Cloud"
    ).count()

    # Count available FortiTokens
    fortitoken_count = db.query(FortiToken).filter(
        FortiToken.status == "available"
    ).count()

    total_count = fortigate_count + fortiauthenticator_count + fortitoken_count + fortidentitycloud_count

    return WarehouseCountResponse(
        fortigate=fortigate_count,
        fortiauthenticator=fortiauthenticator_count,
        fortitoken=fortitoken_count,
        fortidentitycloud=fortidentitycloud_count,
        total=total_count
    )

@router.post("/random")
async def get_random_code(
    code_type: Optional[str] = None,
    db: Session = Depends(get_db),
    email: str = Depends(verify_warehouse_access)
) -> WarehouseCodeResponse:
    """
    Get a random code from the warehouse with optional type filtering.

    Args:
        code_type: Filter by code type ("FortiGate", "FortiAuthenticator", "FortiToken", "FortiIdentityCloud", or None for any)

    Returns:
        Random code or None if no codes available
    """
    # Build query based on type filter
    if code_type == "FortiGate":
        query = db.query(License).filter(
            License.status == "available",
            License.license_type == "FortiGate"
        )
        available_items = query.all()
        if available_items:
            selected_item = random.choice(available_items)
            selected_item.status = "used"
            selected_item.used_at = datetime.utcnow()
            db.commit()

            # Move files to used directory for backward compatibility
            try:
                pdf_file = LICENSE_DIR / selected_item.filename
                code_file = pdf_file.with_suffix('.code')
                type_file = pdf_file.with_suffix('.type')
                used_dir = LICENSE_DIR / "used"
                used_dir.mkdir(exist_ok=True)

                if pdf_file.exists():
                    pdf_file.rename(used_dir / selected_item.filename)
                if code_file.exists():
                    code_file.rename(used_dir / code_file.name)
                if type_file.exists():
                    type_file.rename(used_dir / type_file.name)
            except Exception as e:
                logger.error(f"Error moving files for {selected_item.filename}: {e}")

            # Log warehouse activity
            try:
                # Extract username from email (part before @)
                username = email.split('@')[0] if '@' in email else email
                warehouse_auth_service.log_warehouse_activity(
                    db, email, username, "fetch", "FortiGate",
                    selected_item.code[:5] + "..." if selected_item.code else None
                )
            except Exception as e:
                logger.error(f"Error logging warehouse activity: {e}")

            return WarehouseCodeResponse(
                code=selected_item.code,
                filename=selected_item.filename,
                code_type="FortiGate",
                size=getattr(selected_item, 'size', None)
            )
    elif code_type == "FortiAuthenticator":
        query = db.query(License).filter(
            License.status == "available",
            License.license_type == "FortiAuthenticator"
        )
        available_items = query.all()
        if available_items:
            selected_item = random.choice(available_items)
            selected_item.status = "used"
            selected_item.used_at = datetime.utcnow()
            db.commit()

            # Move files to used directory for backward compatibility
            try:
                pdf_file = LICENSE_DIR / selected_item.filename
                code_file = pdf_file.with_suffix('.code')
                type_file = pdf_file.with_suffix('.type')
                used_dir = LICENSE_DIR / "used"
                used_dir.mkdir(exist_ok=True)

                if pdf_file.exists():
                    pdf_file.rename(used_dir / selected_item.filename)
                if code_file.exists():
                    code_file.rename(used_dir / code_file.name)
                if type_file.exists():
                    type_file.rename(used_dir / type_file.name)
            except Exception as e:
                logger.error(f"Error moving files for {selected_item.filename}: {e}")

            # Log warehouse activity
            try:
                # Extract username from email (part before @)
                username = email.split('@')[0] if '@' in email else email
                warehouse_auth_service.log_warehouse_activity(
                    db, email, username, "fetch", "FortiAuthenticator",
                    selected_item.code[:5] + "..." if selected_item.code else None
                )
            except Exception as e:
                logger.error(f"Error logging warehouse activity: {e}")

            return WarehouseCodeResponse(
                code=selected_item.code,
                filename=selected_item.filename,
                code_type="FortiAuthenticator",
                size=getattr(selected_item, 'size', None)
            )
    elif code_type == "FortiIdentityCloud" or code_type == "FortiIdentity Cloud":
        query = db.query(License).filter(
            License.status == "available",
            License.license_type == "FortiIdentity Cloud"
        )
        available_items = query.all()
        if available_items:
            selected_item = random.choice(available_items)
            selected_item.status = "used"
            selected_item.used_at = datetime.utcnow()
            db.commit()

            # Move files to used directory for backward compatibility
            try:
                pdf_file = LICENSE_DIR / selected_item.filename
                code_file = pdf_file.with_suffix('.code')
                type_file = pdf_file.with_suffix('.type')
                used_dir = LICENSE_DIR / "used"
                used_dir.mkdir(exist_ok=True)

                if pdf_file.exists():
                    pdf_file.rename(used_dir / selected_item.filename)
                if code_file.exists():
                    code_file.rename(used_dir / code_file.name)
                if type_file.exists():
                    type_file.rename(used_dir / type_file.name)
            except Exception as e:
                logger.error(f"Error moving files for {selected_item.filename}: {e}")

            # Log warehouse activity
            try:
                # Extract username from email (part before @)
                username = email.split('@')[0] if '@' in email else email
                warehouse_auth_service.log_warehouse_activity(
                    db, email, username, "fetch", "FortiIdentity Cloud",
                    selected_item.code[:5] + "..." if selected_item.code else None
                )
            except Exception as e:
                logger.error(f"Error logging warehouse activity: {e}")

            return WarehouseCodeResponse(
                code=selected_item.code,
                filename=selected_item.filename,
                code_type="FortiIdentity Cloud",
                size=getattr(selected_item, 'size', None)
            )
    elif code_type == "FortiToken":
        query = db.query(FortiToken).filter(FortiToken.status == "available")
        available_items = query.all()
        if available_items:
            selected_item = random.choice(available_items)
            selected_item.status = "used"
            selected_item.used_at = datetime.utcnow()
            db.commit()

            # Move files to used directory for backward compatibility
            try:
                pdf_file = FORTITOKEN_DIR / selected_item.filename
                code_file = pdf_file.with_suffix('.code')
                used_dir = FORTITOKEN_DIR / "used"
                used_dir.mkdir(exist_ok=True)

                if pdf_file.exists():
                    pdf_file.rename(used_dir / selected_item.filename)
                if code_file.exists():
                    code_file.rename(used_dir / code_file.name)
            except Exception as e:
                logger.error(f"Error moving files for {selected_item.filename}: {e}")

            # Log warehouse activity
            try:
                # Extract username from email (part before @)
                username = email.split('@')[0] if '@' in email else email
                warehouse_auth_service.log_warehouse_activity(
                    db, email, username, "fetch", "FortiToken",
                    selected_item.code[:5] + "..." if selected_item.code else None
                )
            except Exception as e:
                logger.error(f"Error logging warehouse activity: {e}")

            return WarehouseCodeResponse(
                code=selected_item.code,
                filename=selected_item.filename,
                code_type="FortiToken"
            )
    elif code_type is None:
        # Get any available code
        license_query = db.query(License).filter(License.status == "available")
        fortitoken_query = db.query(FortiToken).filter(FortiToken.status == "available")

        available_licenses = license_query.all()
        available_fortitokens = fortitoken_query.all()

        # Combine all available items
        all_available = []
        for license in available_licenses:
            all_available.append(("license", license))
        for fortitoken in available_fortitokens:
            all_available.append(("fortitoken", fortitoken))

        if all_available:
            item_type, selected_item = random.choice(all_available)

            if item_type == "license":
                selected_item.status = "used"
                selected_item.used_at = datetime.utcnow()
                db.commit()

                # Move files to used directory for backward compatibility
                try:
                    pdf_file = LICENSE_DIR / selected_item.filename
                    code_file = pdf_file.with_suffix('.code')
                    type_file = pdf_file.with_suffix('.type')
                    used_dir = LICENSE_DIR / "used"
                    used_dir.mkdir(exist_ok=True)

                    if pdf_file.exists():
                        pdf_file.rename(used_dir / selected_item.filename)
                    if code_file.exists():
                        code_file.rename(used_dir / code_file.name)
                    if type_file.exists():
                        type_file.rename(used_dir / type_file.name)
                except Exception as e:
                    logger.error(f"Error moving files for {selected_item.filename}: {e}")

                # Log warehouse activity
                try:
                    # Extract username from email (part before @)
                    username = email.split('@')[0] if '@' in email else email
                    warehouse_auth_service.log_warehouse_activity(
                        db, email, username, "fetch", selected_item.license_type,
                        selected_item.code[:5] + "..." if selected_item.code else None
                    )
                except Exception as e:
                    logger.error(f"Error logging warehouse activity: {e}")

                return WarehouseCodeResponse(
                    code=selected_item.code,
                    filename=selected_item.filename,
                    code_type=selected_item.license_type,
                    size=getattr(selected_item, 'size', None)
                )
            else:  # fortitoken
                selected_item.status = "used"
                selected_item.used_at = datetime.utcnow()
                db.commit()

                # Move files to used directory for backward compatibility
                try:
                    pdf_file = FORTITOKEN_DIR / selected_item.filename
                    code_file = pdf_file.with_suffix('.code')
                    used_dir = FORTITOKEN_DIR / "used"
                    used_dir.mkdir(exist_ok=True)

                    if pdf_file.exists():
                        pdf_file.rename(used_dir / selected_item.filename)
                    if code_file.exists():
                        code_file.rename(used_dir / code_file.name)
                except Exception as e:
                    logger.error(f"Error moving files for {selected_item.filename}: {e}")

                # Log warehouse activity
                try:
                    # Extract username from email (part before @)
                    username = email.split('@')[0] if '@' in email else email
                    warehouse_auth_service.log_warehouse_activity(
                        db, email, username, "fetch", "FortiToken",
                        selected_item.code[:5] + "..." if selected_item.code else None
                    )
                except Exception as e:
                    logger.error(f"Error logging warehouse activity: {e}")

                return WarehouseCodeResponse(
                    code=selected_item.code,
                    filename=selected_item.filename,
                    code_type="FortiToken"
                )

    # No codes available
    return WarehouseCodeResponse(
        code=None,
        filename=None,
        code_type=None
    )

@router.post("/upload")
async def upload_codes(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    email: str = Depends(verify_warehouse_access)
) -> UploadResponse:
    """
    Upload PDF files containing codes of any type.
    Supports FortiToken activation codes, FortiGate/FortiAuthenticator registration codes,
    and Contract Registration Codes (12-character format).

    Args:
        files: List of PDF files to upload

    Returns:
        Upload result message
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    uploaded_files = []
    duplicate_warnings = []

    for upload in files:
        # Check if file is PDF
        if not upload.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {upload.filename} is not a PDF file")

        # Save file directly to appropriate directory based on type
        try:
            # Read file content into memory first
            upload.file.seek(0)
            file_content = await upload.read()

            # Reset file pointer for potential reuse
            upload.file.seek(0)

            # Save to temporary location first
            temp_path = Path("/tmp") / upload.filename
            with temp_path.open("wb") as buffer:
                buffer.write(file_content)

            # Extract code to determine type
            # Try as FortiToken first
            activation_code = extract_fortitoken_code(str(temp_path))

            if activation_code and activation_code != "Activation code not found." and not activation_code.startswith("Error"):
                # This is a FortiToken
                destination = _resolve_fortitoken_path(upload.filename)
                destination.parent.mkdir(parents=True, exist_ok=True)

                # Copy temp file to destination (avoid cross-device issues)
                with destination.open("wb") as buffer:
                    buffer.write(file_content)

                stats = destination.stat()

                # Check for existing codes with any status to detect duplicates
                existing_fortitoken_by_code = db.query(FortiToken).filter(FortiToken.code == activation_code).first()
                existing_fortitoken_by_filename = db.query(FortiToken).filter(FortiToken.filename == destination.name).first()

                if existing_fortitoken_by_code:
                    # Code already exists in database, likely a duplicate upload
                    if existing_fortitoken_by_code.status == "used":
                        # This is a used token being re-uploaded
                        uploaded_files.append({
                            "name": destination.name,
                            "size": stats.st_size,
                            "type": "FortiToken",
                            "warning": f"Code {activation_code} already exists in database as a used token. File saved but not added to available pool.",
                            "status": "duplicate_used"
                        })
                    else:
                        # This is an available token being re-uploaded
                        uploaded_files.append({
                            "name": destination.name,
                            "size": stats.st_size,
                            "type": "FortiToken",
                            "warning": f"Code {activation_code} already exists in database as an available token. File saved but not duplicated.",
                            "status": "duplicate_available"
                        })
                elif not existing_fortitoken_by_filename:
                    # New token, proceed with normal storage
                    full_text = ""
                    try:
                        doc = fitz.open(str(destination))
                        for page in doc:
                            full_text += page.get_text()
                        doc.close()
                    except Exception as e:
                        logger.error(f"Error reading PDF content for {destination.name}: {e}")

                    new_fortitoken = FortiToken(
                        filename=destination.name,
                        code=activation_code,
                        status="available",
                        original_content=full_text
                    )
                    db.add(new_fortitoken)
                    db.commit()
                    uploaded_files.append({
                        "name": destination.name,
                        "size": stats.st_size,
                        "type": "FortiToken",
                        "status": "new"
                    })
                else:
                    # Filename exists but code check didn't catch it (edge case)
                    uploaded_files.append({
                        "name": destination.name,
                        "size": stats.st_size,
                        "type": "FortiToken",
                        "warning": "File with this name already exists. File saved but not added to database.",
                        "status": "filename_exists"
                    })
            else:
                # Try as License
                result = extract_registration_code(str(temp_path))
                size_info = None
                if isinstance(result, tuple):
                    if len(result) >= 3:
                        registration_code, license_type, size_info = result
                    else:
                        registration_code, license_type = result
                else:
                    registration_code = result
                    license_type = "Unknown"

                if registration_code and registration_code != "Registration code not found." and not registration_code.startswith("Error"):
                    # This is a License
                    destination = _resolve_license_path(upload.filename)
                    destination.parent.mkdir(parents=True, exist_ok=True)

                    # Copy temp file to destination (avoid cross-device issues)
                    with destination.open("wb") as buffer:
                        buffer.write(file_content)

                    stats = destination.stat()

                    # Check for existing codes with any status to detect duplicates
                    existing_license_by_code = db.query(License).filter(License.code == registration_code).first()
                    existing_license_by_filename = db.query(License).filter(License.filename == destination.name).first()

                    if existing_license_by_code:
                        # Code already exists in database, likely a duplicate upload
                        if existing_license_by_code.status == "used":
                            # This is a used license being re-uploaded
                            uploaded_files.append({
                                "name": destination.name,
                                "size": stats.st_size,
                                "type": license_type,
                                "warning": f"Code {registration_code} already exists in database as a used license. File saved but not added to available pool.",
                                "status": "duplicate_used"
                            })
                        else:
                            # This is an available license being re-uploaded
                            uploaded_files.append({
                                "name": destination.name,
                                "size": stats.st_size,
                                "type": license_type,
                                "warning": f"Code {registration_code} already exists in database as an available license. File saved but not duplicated.",
                                "status": "duplicate_available"
                            })
                    elif not existing_license_by_filename:
                        # New license, proceed with normal storage
                        full_text = ""
                        try:
                            doc = fitz.open(str(destination))
                            for page in doc:
                                full_text += page.get_text()
                            doc.close()
                        except Exception as e:
                            logger.error(f"Error reading PDF content for {destination.name}: {e}")

                        new_license = License(
                            filename=destination.name,
                            code=registration_code,
                            license_type=license_type,
                            size=size_info,
                            status="available",
                            original_content=full_text
                        )
                        db.add(new_license)
                        db.commit()
                        uploaded_files.append({
                            "name": destination.name,
                            "size": stats.st_size,
                            "type": license_type,
                            "status": "new"
                        })
                    else:
                        # Filename exists but code check didn't catch it (edge case)
                        uploaded_files.append({
                            "name": destination.name,
                            "size": stats.st_size,
                            "type": license_type,
                            "warning": "File with this name already exists. File saved but not added to database.",
                            "status": "filename_exists"
                        })
                else:
                    # Could not determine type
                    raise HTTPException(status_code=400, detail=f"Could not extract code from {upload.filename}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file {upload.filename}: {str(e)}")
        finally:
            # Clean up temp file if it exists
            temp_path = Path("/tmp") / upload.filename
            temp_path.unlink(missing_ok=True)

    # Generate appropriate message based on what was uploaded
    if any("warning" in file for file in uploaded_files):
        message = "Files processed. Some files contained codes that already exist in the database. Check warnings for details."
    # Log warehouse activity for uploads
    try:
        if uploaded_files:
            # Extract username from email (part before @)
            username = email.split('@')[0] if '@' in email else email
            warehouse_auth_service.log_warehouse_activity(
                db, email, username, "upload", "Codes",
                None, len(uploaded_files)
            )
    except Exception as e:
        logger.error(f"Error logging warehouse activity for upload: {e}")

    if uploaded_files:
        message = "Files uploaded successfully"
    else:
        message = "No files were processed"

    return UploadResponse(
        message=message,
        files=uploaded_files
    )

@router.post("/recycle")
async def recycle_code(
    request: RecycleCodeRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verify_warehouse_access)
) -> dict:
    """
    Recycle any type of code by adding it back to the available pool.

    Args:
        request: Contains the code to recycle

    Returns:
        Success message
    """
    code = request.code.strip()

    # Try to find as License first
    license_entry = db.query(License).filter(License.code == code).first()

    if license_entry:
        # Update status to available and set recycled_at timestamp
        license_entry.status = "available"
        license_entry.recycled_at = datetime.utcnow()
        license_entry.used_at = None
        db.commit()

        # Move files back from used to active directory for backward compatibility
        used_dir = LICENSE_DIR / "used"
        active_dir = LICENSE_DIR

        # Find files in used directory
        pdf_filename = None
        for item in used_dir.iterdir():
            if item.is_file() and item.name.endswith('.code'):
                try:
                    content = item.read_text().strip()
                    if content == code:
                        pdf_filename = item.name.replace('.code', '.pdf')
                        break
                except:
                    continue

        if pdf_filename:
            # Move files back to active directory
            used_pdf_path = used_dir / pdf_filename
            used_code_path = used_pdf_path.with_suffix('.code')
            used_type_path = used_pdf_path.with_suffix('.type')

            active_pdf_path = active_dir / pdf_filename
            active_code_path = active_pdf_path.with_suffix('.code')
            active_type_path = active_pdf_path.with_suffix('.type')

            try:
                # Move files back to active directory
                if used_pdf_path.exists():
                    used_pdf_path.rename(active_pdf_path)
                if used_code_path.exists():
                    used_code_path.rename(active_code_path)
                if used_type_path.exists():
                    used_type_path.rename(active_type_path)
            except Exception as e:
                logger.error(f"Error moving files for recycled code {code}: {e}")

        # Log warehouse activity
        try:
            # Extract username from email (part before @)
            username = email.split('@')[0] if '@' in email else email
            warehouse_auth_service.log_warehouse_activity(
                db, email, username, "recycle", "License",
                code[:5] + "..." if code else None
            )
        except Exception as e:
            logger.error(f"Error logging warehouse activity: {e}")

        return {"message": f"License code {code} recycled successfully"}

    # Try to find as FortiToken
    fortitoken_entry = db.query(FortiToken).filter(FortiToken.code == code).first()

    if fortitoken_entry:
        # Update status to available and set recycled_at timestamp
        fortitoken_entry.status = "available"
        fortitoken_entry.recycled_at = datetime.utcnow()
        fortitoken_entry.used_at = None
        db.commit()

        # Move files back from used to active directory for backward compatibility
        used_dir = FORTITOKEN_DIR / "used"
        active_dir = FORTITOKEN_DIR

        # Find files in used directory
        pdf_filename = None
        for item in used_dir.iterdir():
            if item.is_file() and item.name.endswith('.code'):
                try:
                    content = item.read_text().strip()
                    if content == code:
                        pdf_filename = item.name.replace('.code', '.pdf')
                        break
                except:
                    continue

        if pdf_filename:
            # Move files back to active directory
            used_pdf_path = used_dir / pdf_filename
            used_code_path = used_pdf_path.with_suffix('.code')

            active_pdf_path = active_dir / pdf_filename
            active_code_path = active_pdf_path.with_suffix('.code')

            try:
                # Move files back to active directory
                if used_pdf_path.exists():
                    used_pdf_path.rename(active_pdf_path)
                if used_code_path.exists():
                    used_code_path.rename(active_code_path)
            except Exception as e:
                logger.error(f"Error moving files for recycled code {code}: {e}")

        # Log warehouse activity
        try:
            # Extract username from email (part before @)
            username = email.split('@')[0] if '@' in email else email
            warehouse_auth_service.log_warehouse_activity(
                db, email, username, "recycle", "FortiToken",
                code[:5] + "..." if code else None
            )
        except Exception as e:
            logger.error(f"Error logging warehouse activity: {e}")

        return {"message": f"FortiToken code {code} recycled successfully"}

    # If not found in database, fall back to file-based approach for backward compatibility
    # For Licenses
    used_dir = LICENSE_DIR / "used"
    if used_dir.exists():
        for item in used_dir.iterdir():
            if item.is_file() and item.name.endswith('.code'):
                try:
                    content = item.read_text().strip()
                    if content == code:
                        # Found it, move back to active
                        pdf_filename = item.name.replace('.code', '.pdf')
                        used_pdf_path = used_dir / pdf_filename
                        used_code_path = item

                        active_pdf_path = LICENSE_DIR / pdf_filename
                        active_code_path = active_pdf_path.with_suffix('.code')
                        active_type_path = active_pdf_path.with_suffix('.type')

                        used_type_path = used_pdf_path.with_suffix('.type')

                        # Move files back to active directory
                        if used_pdf_path.exists():
                            used_pdf_path.rename(active_pdf_path)
                        if used_code_path.exists():
                            used_code_path.rename(active_code_path)
                        if used_type_path.exists():
                            used_type_path.rename(active_type_path)

                        # Log warehouse activity
                        try:
                            # Extract username from email (part before @)
                            username = email.split('@')[0] if '@' in email else email
                            warehouse_auth_service.log_warehouse_activity(
                                db, email, username, "recycle", "License",
                                code[:5] + "..." if code else None
                            )
                        except Exception as e:
                            logger.error(f"Error logging warehouse activity: {e}")

                        return {"message": f"License code {code} recycled successfully"}
                except:
                    continue

    # For FortiTokens
    used_dir = FORTITOKEN_DIR / "used"
    if used_dir.exists():
        for item in used_dir.iterdir():
            if item.is_file() and item.name.endswith('.code'):
                try:
                    content = item.read_text().strip()
                    if content == code:
                        # Found it, move back to active
                        pdf_filename = item.name.replace('.code', '.pdf')
                        used_pdf_path = used_dir / pdf_filename
                        used_code_path = item

                        active_pdf_path = FORTITOKEN_DIR / pdf_filename
                        active_code_path = active_pdf_path.with_suffix('.code')

                        # Move files back to active directory
                        if used_pdf_path.exists():
                            used_pdf_path.rename(active_pdf_path)
                        if used_code_path.exists():
                            used_code_path.rename(active_code_path)

                        # Log warehouse activity
                        try:
                            # Extract username from email (part before @)
                            username = email.split('@')[0] if '@' in email else email
                            warehouse_auth_service.log_warehouse_activity(
                                db, email, username, "recycle", "FortiToken",
                                code[:5] + "..." if code else None
                            )
                        except Exception as e:
                            logger.error(f"Error logging warehouse activity: {e}")

                        return {"message": f"FortiToken code {code} recycled successfully"}
                except:
                    continue

    raise HTTPException(status_code=404, detail=f"Code {code} not found for recycling")