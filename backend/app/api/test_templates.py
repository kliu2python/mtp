"""
Test Template API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.services.mongodb import MongoDBAPI

router = APIRouter()
mongo_client = MongoDBAPI()


class TestTemplateCreate(BaseModel):
    """Payload for creating a test template"""
    name: str
    platform: str
    test_scope: str
    test_product: Optional[str] = None
    test_suite: Optional[str] = None
    environment: str
    device_type: Optional[str] = None
    app_version_source: Optional[str] = None
    app_file: Optional[str] = None
    app_version: Optional[str] = None
    timeout: Optional[int] = 3600
    custom_environment: Optional[str] = None


class TestTemplateUpdate(BaseModel):
    """Payload for updating a test template"""
    name: Optional[str] = None
    platform: Optional[str] = None
    test_scope: Optional[str] = None
    test_product: Optional[str] = None
    test_suite: Optional[str] = None
    environment: Optional[str] = None
    device_type: Optional[str] = None
    app_version_source: Optional[str] = None
    app_file: Optional[str] = None
    app_version: Optional[str] = None
    timeout: Optional[int] = None
    custom_environment: Optional[str] = None


class TestTemplateResponse(TestTemplateCreate):
    """Response model for test template"""
    id: str
    created_at: datetime
    updated_at: datetime


@router.get("/tests/templates", response_model=List[dict])
async def list_test_templates():
    """List all test templates"""
    try:
        templates = mongo_client.get_test_templates()
        return templates
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch test templates: {str(e)}")


@router.get("/tests/templates/{template_id}", response_model=dict)
async def get_test_template(template_id: str):
    """Get test template by ID"""
    try:
        template = mongo_client.get_test_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=404, detail="Test template not found")
        return template
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch test template: {str(e)}")


@router.post("/tests/templates", response_model=dict, status_code=201)
async def create_test_template(template_data: TestTemplateCreate):
    """Create a new test template"""
    try:
        template_doc = template_data.dict()
        template_doc["id"] = str(uuid.uuid4())
        template_doc["created_at"] = datetime.utcnow()
        template_doc["updated_at"] = datetime.utcnow()

        result = mongo_client.insert_test_template(template_doc)
        if result:
            return template_doc
        else:
            raise HTTPException(
                status_code=500, detail="Failed to create test template")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create test template: {str(e)}")


@router.put("/tests/templates/{template_id}", response_model=dict)
async def update_test_template(template_id: str, template_data: TestTemplateUpdate):
    """Update test template"""
    try:
        # Check if template exists
        existing_template = mongo_client.get_test_template_by_id(template_id)
        if not existing_template:
            raise HTTPException(
                status_code=404, detail="Test template not found")

        # Update fields
        update_data = template_data.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()

        result = mongo_client.update_test_template(template_id, update_data)
        if result:
            # Return updated template
            updated_template = mongo_client.get_test_template_by_id(template_id)
            return updated_template
        else:
            raise HTTPException(
                status_code=500, detail="Failed to update test template")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update test template: {str(e)}")


@router.delete("/tests/templates/{template_id}", status_code=204)
async def delete_test_template(template_id: str):
    """Delete test template"""
    try:
        result = mongo_client.delete_test_template(template_id)
        if not result:
            raise HTTPException(
                status_code=404, detail="Test template not found")
        return {"detail": "Test template deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete test template: {str(e)}")
