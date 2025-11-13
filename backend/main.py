"""
Test Platform Backend - Main Application
FastAPI-based REST API for test automation platform
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from typing import List

from app.core.config import settings
from app.core.database import engine, Base
from app.api import vms, devices, tests, files, reports, webhooks
from app.services.websocket_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Test Platform...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")
    
    # Start background services
    from app.services.device_monitor import device_monitor
    from app.services.vm_monitor import vm_monitor
    
    # asyncio.create_task(device_monitor.start())
    # asyncio.create_task(vm_monitor.start())
    print("✅ Background services started")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Test Platform...")


app = FastAPI(
    title="Mobile Test Pilot",
    description="Automated testing platform for FortiGate and FortiAuthenticator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(vms.router, prefix="/api/vms", tags=["VMs"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"])
app.include_router(tests.router, prefix="/api/tests", tags=["Tests"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])

# Mount static files
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Mobile Test Pilot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected"
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            await manager.send_personal_message(f"Echo: {data}", client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"Client {client_id} disconnected")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
