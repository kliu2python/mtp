"""
Pydantic schemas for Test Execution API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from uuid import UUID


class TestScope(str, Enum):
    """Test scope enumeration"""
    SMOKE = "smoke"
    REGRESSION = "regression"
    INTEGRATION = "integration"
    CRITICAL = "critical"
    RELEASE = "release"


class TestEnvironment(str, Enum):
    """Test environment enumeration"""
    QA = "qa"
    RELEASE = "release"
    PRODUCTION = "production"


class ExecutionMethod(str, Enum):
    """Test execution method"""
    DOCKER = "docker"
    SSH = "ssh"


class Platform(str, Enum):
    """Mobile platform"""
    IOS = "ios"
    ANDROID = "android"


class TestStatus(str, Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DockerConfig(BaseModel):
    """Docker configuration for test execution"""
    registry: str = Field(default="docker.io", description="Docker registry")
    image: str = Field(..., description="Docker image name")
    tag: str = Field(default="latest", description="Docker image tag")


class TestExecutionRequest(BaseModel):
    """Schema for test execution request"""
    name: str = Field(..., description="Test execution name")
    vm_id: UUID = Field(..., description="VM ID to run tests on")
    apk_id: Optional[int] = Field(None, description="APK/IPA file ID to test (optional)")
    app_version: Optional[str] = Field(None, description="App version string (alternative to apk_id)")
    test_scope: TestScope = Field(..., description="Test scope (smoke, regression, integration, critical, release)")
    environment: TestEnvironment = Field(..., description="Test environment (qa, release, production)")
    platform: Platform = Field(..., description="Platform (ios/android)")
    execution_method: ExecutionMethod = Field(default=ExecutionMethod.DOCKER, description="Execution method")
    test_suite: str = Field(default="FortiToken_Mobile", description="Test suite name")
    docker_config: Optional[DockerConfig] = Field(None, description="Docker configuration (required for docker execution)")
    timeout: int = Field(default=3600, description="Test timeout in seconds")
    additional_params: Optional[Dict[str, Any]] = Field(None, description="Additional test parameters")
    save_as_template: Optional[bool] = Field(False, description="Save this configuration as a template")
    template_name: Optional[str] = Field(None, description="Template name if save_as_template is True")


class TestExecutionResponse(BaseModel):
    """Schema for test execution response"""
    task_id: str = Field(..., description="Test execution task ID")
    status: TestStatus = Field(..., description="Current test status")
    message: str = Field(..., description="Status message")
    vm_id: UUID = Field(..., description="VM ID")
    vm_name: str = Field(..., description="VM name")
    jenkins_job: Optional[str] = Field(None, description="Jenkins job name")
    jenkins_build: Optional[int] = Field(None, description="Jenkins build number")


class TestStatusResponse(BaseModel):
    """Schema for test status response"""
    task_id: str = Field(..., description="Test execution task ID")
    status: TestStatus = Field(..., description="Current test status")
    progress: int = Field(default=0, description="Test progress percentage (0-100)")
    message: str = Field(..., description="Status message")
    vm_id: UUID = Field(..., description="VM ID")
    vm_name: str = Field(..., description="VM name")
    started_at: Optional[datetime] = Field(None, description="Test start time")
    completed_at: Optional[datetime] = Field(None, description="Test completion time")
    jenkins_job: Optional[str] = Field(None, description="Jenkins job name")
    jenkins_build: Optional[int] = Field(None, description="Jenkins build number")
    console_url: Optional[str] = Field(None, description="Jenkins console URL")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Test results (when completed)")


class TestConfigResponse(BaseModel):
    """Schema for previous test configuration"""
    vm_id: UUID
    vm_name: str
    last_test: Optional[Dict[str, Any]] = None
    available_configs: List[Dict[str, Any]] = []


class TestRerunRequest(BaseModel):
    """Schema for rerunning a previous test"""
    task_id: str = Field(..., description="Original task ID to rerun")
    docker_tag: Optional[str] = Field(None, description="Override docker tag (optional)")
    timeout: Optional[int] = Field(None, description="Override timeout (optional)")


class TestTemplate(BaseModel):
    """Schema for test configuration template"""
    id: Optional[int] = None
    name: str = Field(..., description="Template name")
    platform: Platform = Field(..., description="Platform (ios/android)")
    test_scope: TestScope = Field(..., description="Test scope")
    environment: TestEnvironment = Field(..., description="Test environment")
    execution_method: ExecutionMethod = Field(default=ExecutionMethod.DOCKER, description="Execution method")
    test_suite: str = Field(default="FortiToken_Mobile", description="Test suite name")
    docker_tag: str = Field(default="latest", description="Docker image tag")
    timeout: int = Field(default=3600, description="Test timeout in seconds")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TestTemplateListResponse(BaseModel):
    """Schema for list of test templates"""
    templates: List[TestTemplate] = []
    total: int = 0
