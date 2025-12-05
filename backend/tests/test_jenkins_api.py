import os
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

# Clean up environment variables that conflict with strict BaseSettings validation
for key in [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "VITE_API_URL",
    "SSL_CERTIFICATE_PATH",
    "SSL_CERTIFICATE_KEY_PATH",
    "SERVER_FQDN",
]:
    os.environ.pop(key, None)

# Ensure the backend directory is on the import path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from main import app  # noqa: E402
from app.api.jenkins_api import get_db  # noqa: E402
from app.services.jenkins_service import jenkins_service  # noqa: E402
from app.services.settings_service import platform_settings_service  # noqa: E402


class DummySettings:
    def __init__(self, url="http://jenkins.local", username="user", token="token"):
        self.jenkins_url = url
        self.jenkins_username = username
        self.jenkins_api_token = token


class JenkinsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Bypass real database dependency
        def override_get_db():
            yield None

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides = {}

    def test_get_jobs_returns_job_list(self):
        dummy_settings = DummySettings()
        mocked_jobs = [
            {
                "name": "sample-job",
                "url": "http://jenkins.local/job/sample-job/",
                "enabled": True,
                "running": False,
            }
        ]

        with (
            patch.object(platform_settings_service, "get_settings", return_value=dummy_settings) as get_settings,
            patch.object(jenkins_service, "configure") as configure,
            patch.object(jenkins_service, "get_all_jobs", return_value=mocked_jobs) as get_all_jobs,
        ):
            response = self.client.get("/api/jenkins/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mocked_jobs)
        get_settings.assert_called_once()
        configure.assert_called_once_with(
            dummy_settings.jenkins_url, dummy_settings.jenkins_username, dummy_settings.jenkins_api_token
        )
        get_all_jobs.assert_called_once()

    def test_trigger_job_uses_override_credentials(self):
        dummy_settings = DummySettings()
        payload = {
            "job_name": "sample-job",
            "parameters": {"foo": "bar"},
            "jenkins_url": "http://override:8080",
            "username": "override-user",
            "api_token": "override-token",
        }
        trigger_response = {
            "job_name": "sample-job",
            "status": "triggered",
            "queue_id": 42,
            "message": "Job 'sample-job' has been triggered successfully",
            "next_build_number": 101,
        }

        with (
            patch.object(platform_settings_service, "get_settings", return_value=dummy_settings) as get_settings,
            patch.object(jenkins_service, "configure") as configure,
            patch.object(jenkins_service, "trigger_job", return_value=trigger_response) as trigger_job,
        ):
            response = self.client.post("/api/jenkins/jobs/trigger", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), trigger_response)
        get_settings.assert_called_once()
        configure.assert_called_once_with(
            payload["jenkins_url"], payload["username"], payload["api_token"]
        )
        trigger_job.assert_called_once_with(job_name=payload["job_name"], parameters=payload["parameters"])


if __name__ == "__main__":
    unittest.main()
