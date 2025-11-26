"""
Pydantic schemas for Jenkins API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class JenkinsJobTrigger(BaseModel):
    """Schema for triggering a Jenkins job"""
    job_name: str = Field(..., description="Name of the Jenkins job to trigger")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional job parameters")


class JenkinsJobInfo(BaseModel):
    """Schema for Jenkins job information"""
    name: str
    url: str
    description: Optional[str] = None
    enabled: bool
    running: bool
    last_build: Optional[Dict[str, Any]] = None
    next_build_number: int


class JenkinsJobList(BaseModel):
    """Schema for listing Jenkins jobs"""
    name: str
    url: str
    enabled: bool
    running: bool


class JenkinsTriggerResponse(BaseModel):
    """Schema for job trigger response"""
    job_name: str
    status: str
    queue_id: Optional[int] = None
    message: str
    next_build_number: int


class JenkinsBuildStatus(BaseModel):
    """Schema for build status"""
    job_name: str
    build_number: int
    status: Optional[str] = None
    result: Optional[str] = None
    running: bool
    timestamp: Optional[str] = None
    duration: Optional[float] = None
    url: str
    console_url: str


class JenkinsBuildConsole(BaseModel):
    """Schema for build console output"""
    job_name: str
    build_number: int
    console_output: str


class JenkinsStopBuildResponse(BaseModel):
    """Schema for stop build response"""
    job_name: str
    build_number: int
    status: str
    message: str


class JenkinsJobParameter(BaseModel):
    """Schema for job parameters"""
    message: str
    has_parameters: bool
