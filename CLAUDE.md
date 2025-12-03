# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a test automation platform called "Mobile Test Pilot" designed for FortiGate and FortiAuthenticator mobile applications. The platform provides:

1. VM Dashboard for monitoring virtual machines
2. AI-Powered Test Analysis using Claude API
3. File Browser for managing APK/IPA mobile test files
4. Device Management for physical iOS/Android devices
5. Test Execution with Docker-containerized environments

## Architecture

The system follows a modern microservices architecture:

```
┌─────────────────────────────────────────────────────────┐
│                     Web Frontend                        │
│              (React + Ant Design)                       │
└──────────────────┬──────────────────────────────────────┘
                   │ REST API / WebSocket
┌──────────────────▼──────────────────────────────────────┐
│                  Backend API                            │
│               (FastAPI + Python)                        │
└──────────────────┬──────────────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
│PostgreSQL │ │ Redis  │ │  Docker  │
│ Database  │ │ Cache  │ │  Engine  │
└───────────┘ └────────┘ └──────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
              ┌─────▼──────┐      ┌─────▼──────┐
              │  Appium    │      │  Physical  │
              │  Servers   │      │  Devices   │
              └────────────┘      └────────────┘
```

Key components:
- Backend: FastAPI application in Python (located in `backend/`)
- Frontend: React application with Ant Design (located in `frontend/`)
- Database: PostgreSQL with SQLAlchemy ORM
- Message Queue: Redis for caching and background tasks
- Containerization: Docker for isolated test environments
- Mobile Testing: Appium for Android/iOS device automation

## Key Directories and Files

- `backend/` - FastAPI backend application
  - `main.py` - Entry point and application initialization
  - `app/core/` - Core configuration and database setup
  - `app/api/` - API route handlers
  - `app/models/` - Database models
  - `app/services/` - Business logic and integrations
  - `app/schemas/` - Pydantic schemas for data validation
- `frontend/` - React frontend application
- `test-files/` - Storage for APK/IPA files and test data
- `docker-compose.yml` - Main orchestration file
- `deploy.sh` - One-click deployment script

## Development Commands

### Backend Development

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server with hot reloading
uvicorn main:app --reload
```

### Frontend Development

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Building and Deployment

```bash
# Full deployment using docker-compose
docker-compose up -d --build

# Rebuild specific services
docker-compose build backend
docker-compose build frontend

# Update and restart services
docker-compose down
docker-compose up -d --build
```

## Common Operations

### Database Access

```bash
# Access PostgreSQL database
docker exec -it testplatform-db psql -U testuser -d testplatform
```

### Service Monitoring

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Environment Configuration

Environment variables are configured in:
- `.env` file for local development
- `docker-compose.yml` for containerized deployment

Key variables include:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `CLAUDE_API_KEY` - Anthropic Claude API key for AI features
- `SECRET_KEY` - Application secret key for security

### API Documentation

When the platform is running:
- Interactive API docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/redoc

## Technology Stack

### Backend
- FastAPI - Modern Python web framework
- SQLAlchemy - Database ORM
- PostgreSQL - Primary database
- Redis - Caching and background tasks
- Docker SDK - Container management
- Appium Python Client - Mobile test automation
- Anthropic/Claude API - AI analysis capabilities

### Frontend
- React - JavaScript UI library
- Ant Design - Component library
- React Router - Client-side routing
- Axios - HTTP client
- ECharts - Data visualization

### Infrastructure
- Docker - Containerization
- Docker Compose - Multi-container orchestration
- Appium - Mobile testing framework
- NGINX - Web server and reverse proxy

## Code Patterns and Conventions

### Backend Structure
1. API endpoints are defined in `backend/app/api/` modules
2. Database models in `backend/app/models/`
3. Business logic in `backend/app/services/`
4. Data validation using Pydantic schemas in `backend/app/schemas/`
5. Configuration in `backend/app/core/config.py`

### Frontend Structure
1. Components organized by feature in `frontend/src/components/`
2. Pages in `frontend/src/pages/`
3. Constants and shared utilities in `frontend/src/constants.js`
4. Main application layout in `frontend/src/App.jsx`

### Error Handling
- Backend uses FastAPI's exception handling
- Frontend uses try/catch patterns with user-friendly error messages
- Proper logging throughout the application

### Security
- JWT-based authentication
- CORS middleware configuration
- Secure password hashing with bcrypt
- Input validation using Pydantic schemas