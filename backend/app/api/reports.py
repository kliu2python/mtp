"""Reports API"""
from fastapi import APIRouter
router = APIRouter()

@router.get("/generate")
async def generate_report():
    return {"message": "Report generation"}
