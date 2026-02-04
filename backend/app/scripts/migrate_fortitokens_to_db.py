"""
Migration script to migrate existing file-based FortiToken data to database
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path so we can import the models
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.core.database import _build_engine_kwargs
from app.models.fortitoken import FortiToken
import fitz  # PyMuPDF
import re

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
        print(f"Error extracting code from {pdf_path}: {e}")
        return f"Error extracting code: {str(e)}"
    finally:
        # Close the document if it was opened
        try:
            doc.close()
        except:
            pass

def migrate_fortitokens_to_db():
    """Migrate existing file-based FortiToken data to database"""

    # Create database engine
    engine_kwargs = _build_engine_kwargs(settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Define the FortiToken directory
        FORTITOKEN_DIR = Path(__file__).resolve().parent.parent / "api" / "uploads" / "fortitokens"

        # Check if used directory exists
        used_dir = FORTITOKEN_DIR / "used"
        used_files = set()
        if used_dir.exists():
            # Get list of used files
            for item in used_dir.iterdir():
                if item.is_file():
                    used_files.add(item.name)

        # Process all PDF files in the FortiToken directory
        for item in FORTITOKEN_DIR.iterdir():
            # Skip used directory and non-PDF files
            if item.name == "used" or not item.is_file() or not item.name.endswith('.pdf'):
                continue

            # Skip files that are already in used folder
            if item.name in used_files:
                continue

            # Check if FortiToken already exists in database
            existing_fortitoken = db.query(FortiToken).filter(FortiToken.filename == item.name).first()

            if not existing_fortitoken:
                print(f"Processing {item.name}...")

                # Extract activation code from the PDF
                activation_code = extract_fortitoken_code(str(item))

                # Store in database if code was extracted successfully
                if activation_code and activation_code != "Activation code not found." and not activation_code.startswith("Error"):
                    # Read the PDF content for full text storage
                    full_text = ""
                    try:
                        doc = fitz.open(str(item))
                        for page in doc:
                            full_text += page.get_text()
                        doc.close()
                    except Exception as e:
                        print(f"Error reading PDF content for {item.name}: {e}")
                        full_text = ""

                    # Determine status based on whether it's in used directory
                    status = "used" if item.name in used_files else "available"

                    # Create new FortiToken entry
                    new_fortitoken = FortiToken(
                        filename=item.name,
                        code=activation_code,
                        status=status,
                        original_content=full_text
                    )
                    db.add(new_fortitoken)

                    print(f"Added {item.name} to database with code {activation_code}")
                else:
                    print(f"Could not extract code from {item.name}")

        # Commit all changes
        db.commit()
        print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_fortitokens_to_db()