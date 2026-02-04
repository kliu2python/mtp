"""
Migration script to migrate existing file-based license data to database
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
from app.models.license import License
from app.api.warehouse import extract_registration_code

def migrate_licenses_to_db():
    """Migrate existing file-based license data to database"""

    # Create database engine
    engine_kwargs = _build_engine_kwargs(settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Define the license directory
        LICENSE_DIR = Path(__file__).resolve().parent.parent / "api" / "uploads" / "licenses"

        # Check if used directory exists
        used_dir = LICENSE_DIR / "used"
        used_files = set()
        if used_dir.exists():
            # Get list of used files
            for item in used_dir.iterdir():
                if item.is_file():
                    used_files.add(item.name)

        # Process all PDF files in the license directory
        for item in LICENSE_DIR.iterdir():
            # Skip used directory and non-PDF files
            if item.name == "used" or not item.is_file() or not item.name.endswith('.pdf'):
                continue

            # Skip files that are already in used folder
            if item.name in used_files:
                continue

            # Check if license already exists in database
            existing_license = db.query(License).filter(License.filename == item.name).first()

            if not existing_license:
                print(f"Processing {item.name}...")

                # Extract code and type from the PDF
                result = extract_registration_code(str(item))
                if isinstance(result, tuple):
                    registration_code, license_type = result
                else:
                    registration_code = result
                    license_type = "Unknown"

                # Store in database if code was extracted successfully
                if registration_code and registration_code != "Registration code not found." and not registration_code.startswith("Error"):
                    # Read the PDF content for full text storage
                    full_text = ""
                    try:
                        import fitz  # PyMuPDF
                        doc = fitz.open(str(item))
                        for page in doc:
                            full_text += page.get_text()
                        doc.close()
                    except Exception as e:
                        print(f"Error reading PDF content for {item.name}: {e}")
                        full_text = ""

                    # Determine status based on whether it's in used directory
                    status = "used" if item.name in used_files else "available"

                    # Create new license entry
                    new_license = License(
                        filename=item.name,
                        code=registration_code,
                        license_type=license_type,
                        status=status,
                        original_content=full_text
                    )
                    db.add(new_license)

                    print(f"Added {item.name} to database with code {registration_code}")
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
    migrate_licenses_to_db()