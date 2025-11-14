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
from app.api import vms, devices, tests, files, reports, webhooks, jenkins_nodes, dashboard, apks, stf, schedules, ai_analysis
from app.services.websocket_manager import manager
from sqlalchemy import inspect, text


def _ensure_optional_columns():
    """Make sure optional columns added after initial deployment exist."""
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("virtual_machines")}

    statements = []
    if "ssh_username" not in existing_columns:
        statements.append(text("ALTER TABLE virtual_machines ADD COLUMN ssh_username VARCHAR NULL"))
    if "ssh_password" not in existing_columns:
        statements.append(text("ALTER TABLE virtual_machines ADD COLUMN ssh_password VARCHAR NULL"))

    if not statements:
        # Still need to check for data migration even if no schema changes
        pass
    else:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(statement)

    # Migrate existing lowercase provider values to uppercase
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE virtual_machines SET provider = 'DOCKER' WHERE provider = 'docker'"
        ))
        connection.execute(text(
            "UPDATE virtual_machines SET provider = 'OPENSTACK' WHERE provider = 'openstack'"
        ))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Test Platform...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    _ensure_optional_columns()
    print("✅ Database initialized")

    # Start background services
    from app.services.device_monitor import device_monitor
    from app.services.vm_monitor import vm_monitor
    from app.services.scheduler_service import scheduler_service

    # asyncio.create_task(device_monitor.start())
    # asyncio.create_task(vm_monitor.start())

    # Start scheduler service
    try:
        await scheduler_service.start()
    except Exception as e:
        print(f"⚠️  Scheduler service failed to start: {e}")

    print("✅ Background services started")

    yield

    # Shutdown
    print("🛑 Shutting down Test Platform...")

    # Stop scheduler service
    try:
        await scheduler_service.stop()
    except Exception as e:
        print(f"⚠️  Error stopping scheduler: {e}")


app = FastAPI(
    title="Mobile Test Pilot",
    description="Automated testing platform for FortiGate and FortiAuthenticator",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(vms.router, prefix="/api/vms", tags=["VMs"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"])
app.include_router(tests.router, prefix="/api/tests", tags=["Tests"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(apks.router, prefix="/api/apks", tags=["APKs"])
app.include_router(stf.router, prefix="/api/stf", tags=["STF"])
app.include_router(schedules.router, prefix="/api/schedules", tags=["Schedules"])
app.include_router(ai_analysis.router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(jenkins_nodes.router, prefix="/api/jenkins", tags=["Jenkins Nodes"])
app.include_router(dashboard.router, tags=["Dashboard"])

# Mount uploaded files for direct download links
app.mount("/uploads", StaticFiles(directory=str(files.UPLOAD_DIR)), name="uploads")


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
