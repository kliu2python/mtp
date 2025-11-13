"""Webhooks API"""
from fastapi import APIRouter
router = APIRouter()

@router.post("/github")
async def github_webhook(payload: dict):
    return {"message": "Webhook received"}
