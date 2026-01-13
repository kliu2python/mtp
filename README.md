# Test Automation Platform

A complete web-based test automation platform for FortiGate and FortiAuthenticator, similar to Jenkins but specialized for mobile app testing.

## 🌟 Features

### 1. VM Dashboard
- Monitor FortiGate and FortiAuthenticator virtual machines
- Track test metrics (pass rate, failure rate, execution time)
- Real-time resource monitoring (CPU, memory, disk usage)
- Docker-based VM isolation
- Start/Stop VMs with one click

### 2. AI-Powered Test Analysis
- Automatic code analysis using Claude API
- Calculate automation coverage vs manual tests
- Compare with CSV-uploaded manual test cases
- Intelligent failure analysis and recommendations

### 3. File Browser
- Manage APK/IPA mobile test files
- Automatic metadata extraction (version, signature, permissions)
- Drag-and-drop file upload
- Preview and download capabilities

### 4. Device Management
- Auto-discover physical iOS and Android devices
- Support for emulators and cloud devices
- Real-time device status monitoring (battery, storage, availability)
- One-click device selection for test execution
- Health check and heartbeat monitoring

### 5. Test Execution
- Docker-containerized test environments
- Parallel test execution
- Real-time log streaming via WebSocket
- Automatic retry on failures
- Detailed test reports

## 🚀 Quick Start

### Prerequisites
- Docker (20.10+)
- Docker Compose (2.0+)
- 4GB+ RAM
- 10GB+ disk space

### One-Command Deployment

```bash
./deploy.sh
```

That's it! The script will:
1. Check prerequisites
2. Create necessary directories
3. Generate .env file
4. Build and start all services
5. Initialize database with sample data

### Access the Platform

After deployment completes:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432 (user: testuser, pass: testpass)
- **Redis**: localhost:6379

## 📊 Architecture

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

## 📁 Project Structure

```
test-platform/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── core/           # Core configuration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React frontend
│   ├── src/
│   │   ├── pages/          # Page components
│   │   └── components/     # Reusable components
│   ├── Dockerfile
│   └── package.json
├── test-files/             # Test file storage
│   ├── mobile-apps/        # APK/IPA files
│   ├── test-scripts/       # Test scripts
│   └── test-data/          # Test data
├── docker-compose.yml      # Docker Compose config
├── deploy.sh               # One-click deployment
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

Edit `.env` file to configure:

```bash
# Database
DATABASE_URL=postgresql://testuser:testpass@db:5432/testplatform

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key-here

# AI Services (Optional)
CLAUDE_API_KEY=your-claude-api-key
OPENAI_API_KEY=your-openai-api-key

# Appium
APPIUM_ANDROID_URL=http://appium-android:4723
APPIUM_IOS_URL=http://appium-ios:4724
```

### Adding AI Capabilities

To enable AI-powered features:

1. Get your API key from [Anthropic](https://www.anthropic.com)
2. Add it to `.env`: `CLAUDE_API_KEY=your-key-here`
3. Restart services: `docker-compose restart backend`

## 📱 Connecting Physical Devices

### Android Devices

1. Enable USB debugging on your Android device
2. Connect via USB
3. Verify connection: `adb devices`
4. In the platform, go to Devices → Refresh Devices

### iOS Devices

1. Install libimobiledevice: `brew install libimobiledevice`
2. Connect iOS device via USB
3. Trust the computer on your device
4. Verify: `idevice_id -l`
5. In the platform, go to Devices → Refresh Devices

## 🧪 Running Tests

### Via Web UI

1. Go to Tests page
2. Click "New Test Job"
3. Select VM and devices
4. Choose test scripts
5. Click "Start Test"

### Via API

```bash
curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Test",
    "vm_id": "vm-uuid",
    "device_ids": ["device-uuid"],
    "test_scripts": ["test_login.py"]
  }'
```

## 📊 Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Database Access

```bash
docker exec -it testplatform-db psql -U testuser -d testplatform
```

### Redis Access

```bash
docker exec -it testplatform-redis redis-cli
```

## 🛠 Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
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

## 🔄 Common Operations

### Stop All Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### Update Code and Rebuild
```bash
docker-compose down
docker-compose up -d --build
```

### Remove Everything (Including Data)
```bash
docker-compose down -v
```

### Backup Database
```bash
docker exec testplatform-db pg_dump -U testuser testplatform > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker exec -i testplatform-db psql -U testuser -d testplatform
```

## 📚 API Documentation

Once the platform is running, visit:

http://localhost:8000/docs

This provides interactive Swagger documentation for all API endpoints.

## 🎯 Usage Examples

### 1. Create a VM

```python
import requests

response = requests.post('http://localhost:8000/api/vms', json={
    'name': 'FortiGate-Test-VM',
    'platform': 'FortiGate',
    'version': '7.4.2',
    'test_priority': 5
})
print(response.json())
```

### 2. List Available Devices

```python
response = requests.get('http://localhost:8000/api/devices', params={
    'status': 'available'
})
devices = response.json()['devices']
```

### 3. Upload Test File

```python
files = {'file': open('FortiClient.apk', 'rb')}
response = requests.post('http://localhost:8000/api/files/upload', files=files)
```

## 🐛 Troubleshooting

### Backend Won't Start
- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs backend`
- Verify database is healthy: `docker-compose ps db`

### Can't Connect to Database
- Ensure PostgreSQL container is running
- Check connection string in `.env`
- Wait for database to be healthy: `docker-compose logs db`

### Devices Not Detected
- For Android: Run `adb devices` to verify connection
- For iOS: Run `idevice_id -l` to verify connection
- Check Appium logs: `docker-compose logs appium-android`

### Port Already in Use
- Change ports in `docker-compose.yml`
- Or stop conflicting services

## 🔒 Security Notes

⚠️ **Important**: This is a development setup. For production:

1. Change all default passwords in `.env`
2. Use HTTPS (add nginx with SSL)
3. Enable authentication (implement JWT)
4. Restrict Docker socket access
5. Use secrets management (HashiCorp Vault, AWS Secrets Manager)
6. Enable firewall rules
7. Regular security updates

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

MIT License - See LICENSE file for details

## 🆘 Support

- Documentation: Check `/docs` folder
- Jenkins Cloud runner API: See `docs/JENKINS_CLOUD_API.md` for the Jenkins Cloud endpoints used to trigger and monitor multi-platform test runs.
- API Docs: http://localhost:8000/docs
- Issues: Create a GitHub issue
- Email: support@example.com

## 🎉 Credits

Built with:
- FastAPI
- React
- Ant Design
- Docker
- PostgreSQL
- Redis
- Appium

## 📈 Roadmap

- [ ] Kubernetes deployment support
- [ ] Advanced test scheduling
- [ ] Integration with CI/CD pipelines
- [ ] Real-time test result dashboards
- [ ] Machine learning for test failure prediction
- [ ] Multi-tenant support
- [ ] Advanced reporting and analytics
- [ ] Cloud device farm integration (AWS, BrowserStack)

---

**Happy Testing! 🚀**
