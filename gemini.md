# Gemini Development Guide - MTP (Mobile Test Pilot)

This document provides essential context and technical details for AI assistants (like Gemini) to understand and contribute to the MTP project.

## 🚀 Project Overview
MTP (Mobile Test Pilot) is a specialized test automation platform for Fortinet products (FortiGate, FortiAuthenticator, FortiToken Mobile). It mimics a Jenkins-like architecture but is tailored for mobile app testing and virtual machine management.

## 🏗 Architecture
- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: React (Vite, Ant Design, ECharts)
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Task Queue**: Celery with Redis
- **Orchestration**: Docker & Docker Compose
- **Execution Engine**: Custom Jenkins-style SSH controller
- **Mobile Automation**: Appium

## 📁 Key Components

### 1. Jenkins Workflow Engine
A 100% faithful reproduction of Jenkins' master/worker model.
- **Controller**: `backend/app/services/jenkins_controller.py`
- **Models**: `JenkinsJob`, `JenkinsBuild`, `JenkinsNode`
- **Logic**: SSHs into worker nodes, creates workspaces, pulls Docker images, and executes tests while streaming logs via WebSockets.
- **Key Files**: `JENKINS_EXECUTION_ENGINE.md`, `JENKINS_IMPLEMENTATION_SUMMARY.md`

### 2. Unified Warehouse
Manages registration codes and activation tokens.
- **Functionality**: Extracts codes from PDF licenses (FortiGate, FAC, FortiToken) using PyMuPDF (`fitz`).
- **Storage**: `backend/app/uploads/licenses` and `backend/app/uploads/fortitokens`.
- **API**: `backend/app/api/warehouse/__init__.py`

### 3. VM & Device Management
- **VMs**: Tracks FortiGate/FAC virtual machines.
- **Devices**: Auto-discovery of physical Android/iOS devices.
- **STF Integration**: Uses OpenSTF for remote device control.

### 4. AI-Powered Analysis
- **Integration**: Anthropic (Claude) and OpenAI.
- **Features**: Automation coverage analysis, failure recommendations, and intelligent test case comparison.
- **Service**: `backend/app/services/ai_analyzer.py`

## 🛠 Development Workflow

### Backend (FastAPI)
- **Location**: `/backend`
- **Commands**: 
  - Install: `pip install -r requirements.txt`
  - Run: `uvicorn main:app --reload --port 8000`
- **Standards**: Pydantic v2 for schemas, SQLAlchemy 2.0 for ORM.

### Frontend (React)
- **Location**: `/frontend`
- **Commands**:
  - Install: `npm install`
  - Run: `npm run dev`
- **UI Framework**: Ant Design (v5). Components are in `src/components/`.

### Docker Environment
- **Deployment**: `./deploy.sh` handles environment setup and `docker-compose up`.
- **Containers**: `backend`, `frontend`, `db`, `redis`, `worker`.

## 📜 Key Documentation Files
- `README.md`: General overview and quick start.
- `AUTHENTICATION_GUIDE.md`: Details on SAML and local auth.
- `JENKINS_WORKFLOW_GUIDE.md`: Comprehensive guide to the execution engine.
- `CLAUDE.md`: Implementation notes for AI features.

## 🤖 AI Guidelines for This Project
1. **Maintain Jenkins Parity**: When modifying the execution engine, ensure it adheres to the master/worker SSH model described in `JENKINS_IMPLEMENTATION_SUMMARY.md`.
2. **Database Migrations**: Use Alembic or the provided migration scripts in `backend/app/scripts/`.
3. **Typing**: Use Python type hints and Pydantic models for all API endpoints.
4. **UI Style**: Use Ant Design components and follow the established dashboard layout in `App.jsx`.
5. **PDF Processing**: Use `PyMuPDF` (fitz) for any warehouse-related extraction tasks.

## 🔗 Important Paths
- **API Docs**: `http://localhost:8000/docs` (Swagger)
- **DB File (Dev)**: `backend/data/testplatform.db` (SQLite used in some dev setups, though PostgreSQL is preferred).
- **Uploads**: `backend/app/api/uploads/`
