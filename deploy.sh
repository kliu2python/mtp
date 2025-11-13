#!/bin/bash

# Test Platform - One-Click Deployment Script
# This script will deploy the entire test automation platform

set -e

echo "=================================================="
echo "  Test Automation Platform - Deployment Script"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is installed${NC}"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p test-files/{mobile-apps/{android,ios},test-scripts,test-data}
mkdir -p backend/app/{api,models,services,core}
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'ENVFILE'
# Database
DATABASE_URL=postgresql://testuser:testpass@db:5432/testplatform
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpass
POSTGRES_DB=testplatform

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key-please-change-in-production-$(openssl rand -hex 32)

# AI Services (Optional - add your keys)
CLAUDE_API_KEY=
OPENAI_API_KEY=

# Appium
APPIUM_ANDROID_URL=http://appium-android:4723
APPIUM_IOS_URL=http://appium-ios:4724

# Frontend
VITE_API_URL=http://localhost:8000
ENVFILE
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env file to add your API keys if needed${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi
echo ""

# Build and start containers
echo "🐳 Building and starting Docker containers..."
echo "This may take a few minutes on first run..."
echo ""

if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo ""
echo -e "${GREEN}✅ Containers started successfully${NC}"
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if backend is healthy
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is healthy${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo -n "."
    sleep 2
done
echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${YELLOW}⚠️  Backend may not be fully ready yet, but deployment is complete${NC}"
fi

# Initialize database with sample data
echo ""
echo "📊 Initializing database with sample data..."
docker exec testplatform-backend python -c "
from app.core.database import engine, Base, SessionLocal
from app.models.vm import VirtualMachine, VMPlatform, VMStatus
from app.models.device import TestDevice, DeviceType, DeviceStatus

# Create tables
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Create sample VMs
vms = [
    VirtualMachine(
        name='FortiGate-7.4.2-VM1',
        platform=VMPlatform.FORTIGATE,
        version='7.4.2',
        test_priority=5,
        ip_address='192.168.1.101'
    ),
    VirtualMachine(
        name='FortiGate-7.2.8-VM2',
        platform=VMPlatform.FORTIGATE,
        version='7.2.8',
        test_priority=4,
        ip_address='192.168.1.102'
    ),
    VirtualMachine(
        name='FortiAuthenticator-6.5.1',
        platform=VMPlatform.FORTIAUTHENTICATOR,
        version='6.5.1',
        test_priority=3,
        ip_address='192.168.1.103'
    )
]

for vm in vms:
    if not db.query(VirtualMachine).filter_by(name=vm.name).first():
        db.add(vm)

# Create sample devices
devices = [
    TestDevice(
        name='iPhone-14-Pro',
        device_type=DeviceType.PHYSICAL_IOS,
        platform='iOS',
        os_version='16.0',
        device_id='demo-iphone-001',
        battery_level=85
    ),
    TestDevice(
        name='Samsung-Galaxy-S23',
        device_type=DeviceType.PHYSICAL_ANDROID,
        platform='Android',
        os_version='13.0',
        device_id='demo-android-001',
        adb_id='demo-android-001',
        battery_level=92
    ),
    TestDevice(
        name='iOS-Simulator',
        device_type=DeviceType.EMULATOR_IOS,
        platform='iOS',
        os_version='17.0',
        device_id='demo-sim-ios-001',
        battery_level=100
    )
]

for device in devices:
    if not db.query(TestDevice).filter_by(device_id=device.device_id).first():
        db.add(device)

db.commit()
print('✅ Sample data created')
" || echo -e "${YELLOW}⚠️  Could not initialize sample data (this is optional)${NC}"

echo ""
echo "=================================================="
echo -e "${GREEN}  🎉 Deployment Complete! 🎉${NC}"
echo "=================================================="
echo ""
echo "🌐 Access the application at:"
echo ""
echo -e "  ${GREEN}Frontend:${NC} http://localhost:3000"
echo -e "  ${GREEN}Backend API:${NC} http://localhost:8000"
echo -e "  ${GREEN}API Documentation:${NC} http://localhost:8000/docs"
echo -e "  ${GREEN}Database:${NC} localhost:5432"
echo -e "  ${GREEN}Redis:${NC} localhost:6379"
echo ""
echo "📚 Useful commands:"
echo ""
echo "  View logs:        docker-compose logs -f"
echo "  View backend logs: docker-compose logs -f backend"
echo "  Stop services:    docker-compose down"
echo "  Restart services: docker-compose restart"
echo "  Remove all:       docker-compose down -v"
echo ""
echo "=================================================="
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "  1. Open http://localhost:8000/docs to explore the API"
echo "  2. Open http://localhost:3000 for the web interface"
echo "  3. Add your AI API keys in .env file if needed"
echo "  4. Upload test files to test-files/ directory"
echo "  5. Connect physical devices and run 'adb devices'"
echo ""
echo -e "${GREEN}Happy Testing! 🚀${NC}"
echo ""
