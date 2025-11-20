"""
Jenkins Jobs API
API endpoints for managing Jenkins-style jobs and builds
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.config import settings
from app.models.jenkins_job import JenkinsJob, JobType
from app.models.jenkins_build import JenkinsBuild, BuildStatus
from app.services.jenkins_service import jenkins_service

router = APIRouter(prefix="/api/jenkins", tags=["Jenkins Jobs"])


# =============================================================================
# Request/Response Models
# =============================================================================

class JobCreateRequest(BaseModel):
    """Request model for creating a job"""
    name: str = Field(..., description="Job name (must be unique)")
    description: Optional[str] = Field(None, description="Job description")
    job_type: JobType = Field(JobType.DOCKER, description="Job type (freestyle, pipeline, docker)")
    script: Optional[str] = Field(None, description="Shell script or Jenkinsfile content")
    required_labels: List[str] = Field(default_factory=list, description="Required agent labels")

    # Docker configuration
    docker_registry: Optional[str] = Field("10.160.16.60", description="Docker registry")
    docker_image: Optional[str] = Field("pytest-automation/pytest_automation", description="Docker image")
    docker_tag: str = Field("latest", description="Docker image tag")

    # Test configuration
    test_suite: Optional[str] = Field(None, description="Test suite path")
    test_markers: Optional[str] = Field(None, description="Pytest markers")
    lab_config: Optional[str] = Field(None, description="Lab config file path")
    platform: Optional[str] = Field("ios", description="Platform (ios, android)")

    # Workspace configuration
    workspace_path: str = Field("/home/jenkins/workspace", description="Workspace base path")
    config_mount_source: str = Field("/home/jenkins/custom_config", description="Config mount source")

    # Build options
    max_concurrent_builds: int = Field(1, description="Max concurrent builds")
    build_timeout: int = Field(7200, description="Build timeout in seconds")
    keep_builds: int = Field(30, description="Number of builds to keep")

    # Notifications
    email_recipients: Optional[str] = Field(None, description="Email recipients (comma-separated)")
    notify_on_success: bool = Field(True, description="Notify on success")
    notify_on_failure: bool = Field(True, description="Notify on failure")

    parameters: Dict[str, Any] = Field(default_factory=dict, description="Job parameters")
    environment_vars: Dict[str, Any] = Field(default_factory=dict, description="Environment variables")


class JobUpdateRequest(BaseModel):
    """Request model for updating a job"""
    description: Optional[str] = None
    script: Optional[str] = None
    required_labels: Optional[List[str]] = None
    docker_registry: Optional[str] = None
    docker_image: Optional[str] = None
    docker_tag: Optional[str] = None
    test_suite: Optional[str] = None
    test_markers: Optional[str] = None
    lab_config: Optional[str] = None
    platform: Optional[str] = None
    workspace_path: Optional[str] = None
    config_mount_source: Optional[str] = None
    max_concurrent_builds: Optional[int] = None
    build_timeout: Optional[int] = None
    keep_builds: Optional[int] = None
    email_recipients: Optional[str] = None
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    enabled: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None
    environment_vars: Optional[Dict[str, Any]] = None


class BuildTriggerRequest(BaseModel):
    """Request model for triggering a build"""
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Build parameters")
    triggered_by: str = Field("API", description="Who triggered the build")


# =============================================================================
# Job Management Endpoints
# =============================================================================

@router.post("/jobs", response_model=dict)
async def create_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new Jenkins job

    This is equivalent to creating a new job in Jenkins UI
    """
    # Check if job name already exists
    existing = db.execute(
        select(JenkinsJob).where(JenkinsJob.name == request.name)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail=f"Job '{request.name}' already exists")

    # Create new job
    job = JenkinsJob(
        name=request.name,
        description=request.description,
        job_type=request.job_type,
        script=request.script,
        required_labels=request.required_labels,
        docker_registry=request.docker_registry,
        docker_image=request.docker_image,
        docker_tag=request.docker_tag,
        test_suite=request.test_suite,
        test_markers=request.test_markers,
        lab_config=request.lab_config,
        platform=request.platform,
        workspace_path=request.workspace_path,
        config_mount_source=request.config_mount_source,
        max_concurrent_builds=request.max_concurrent_builds,
        build_timeout=request.build_timeout,
        keep_builds=request.keep_builds,
        email_recipients=request.email_recipients,
        notify_on_success=request.notify_on_success,
        notify_on_failure=request.notify_on_failure,
        parameters=request.parameters,
        environment_vars=request.environment_vars,
        created_by="API"
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Create job in Jenkins
    try:
        await jenkins_service.create_job_in_jenkins(job)
    except Exception as e:
        # Rollback if Jenkins creation fails
        db.delete(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to create job in Jenkins: {str(e)}")

    return {
        "message": f"Job '{job.name}' created successfully in Jenkins and local database",
        "job": job.to_dict()
    }


@router.get("/jobs", response_model=List[dict])
async def list_jobs(
    enabled_only: bool = Query(False, description="Show only enabled jobs"),
    db: Session = Depends(get_db)
):
    """
    List all Jenkins jobs

    This is equivalent to the Jenkins jobs list view
    """
    query = select(JenkinsJob).order_by(JenkinsJob.name)

    if enabled_only:
        query = query.where(JenkinsJob.enabled == True)

    jobs = db.execute(query).scalars().all()

    return [job.to_dict() for job in jobs]


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job details"""
    job = db.get(JenkinsJob, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.to_dict()


@router.get("/jobs/name/{job_name}", response_model=dict)
async def get_job_by_name(
    job_name: str,
    db: Session = Depends(get_db)
):
    """Get job details by name"""
    job = db.execute(
        select(JenkinsJob).where(JenkinsJob.name == job_name)
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_name}' not found")

    return job.to_dict()


@router.put("/jobs/{job_id}", response_model=dict)
async def update_job(
    job_id: str,
    request: JobUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update a job"""
    job = db.get(JenkinsJob, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    return {
        "message": f"Job '{job.name}' updated successfully",
        "job": job.to_dict()
    }


@router.delete("/jobs/{job_id}", response_model=dict)
async def delete_job(
    job_id: str,
    delete_builds: bool = Query(False, description="Also delete all builds"),
    db: Session = Depends(get_db)
):
    """Delete a job"""
    job = db.get(JenkinsJob, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_name = job.name

    # Delete from Jenkins first
    try:
        await jenkins_service.delete_job_from_jenkins(job_name)
    except Exception as e:
        logger.warning(f"Failed to delete job from Jenkins: {e}")

    # Delete builds if requested
    if delete_builds:
        db.execute(
            select(JenkinsBuild).where(JenkinsBuild.job_id == job_id)
        ).delete()

    db.delete(job)
    db.commit()

    return {
        "message": f"Job '{job_name}' deleted successfully from Jenkins and local database"
    }


@router.post("/jobs/{job_id}/enable", response_model=dict)
async def enable_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Enable a job"""
    job = db.get(JenkinsJob, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Enable in Jenkins
    try:
        await jenkins_service.enable_job_in_jenkins(job.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable job in Jenkins: {str(e)}")

    job.enabled = True
    db.commit()

    return {
        "message": f"Job '{job.name}' enabled in Jenkins",
        "job": job.to_dict()
    }


@router.post("/jobs/{job_id}/disable", response_model=dict)
async def disable_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Disable a job"""
    job = db.get(JenkinsJob, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Disable in Jenkins
    try:
        await jenkins_service.disable_job_in_jenkins(job.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable job in Jenkins: {str(e)}")

    job.enabled = False
    db.commit()

    return {
        "message": f"Job '{job.name}' disabled in Jenkins",
        "job": job.to_dict()
    }


# =============================================================================
# Build Management Endpoints
# =============================================================================

@router.post("/jobs/{job_id}/build", response_model=dict)
async def trigger_build(
    job_id: str,
    request: BuildTriggerRequest = BuildTriggerRequest(),
    db: Session = Depends(get_db)
):
    """
    Trigger a new build for a job

    This is equivalent to clicking "Build Now" in Jenkins
    """
    try:
        build = await jenkins_service.trigger_build(
            db=db,
            job_id=job_id,
            parameters=request.parameters,
            triggered_by=request.triggered_by
        )

        return {
            "message": f"Build #{build.build_number} triggered in Jenkins",
            "build": build.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/builds", response_model=List[dict])
async def list_builds(
    job_id: str,
    limit: int = Query(10, description="Number of builds to return"),
    offset: int = Query(0, description="Offset for pagination"),
    status: Optional[BuildStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List builds for a job

    This is equivalent to the Jenkins build history view
    """
    query = select(JenkinsBuild).where(JenkinsBuild.job_id == job_id)

    if status:
        query = query.where(JenkinsBuild.status == status)

    query = query.order_by(desc(JenkinsBuild.build_number)).offset(offset).limit(limit)

    builds = db.execute(query).scalars().all()

    return [build.to_dict() for build in builds]


@router.get("/builds/{build_id}", response_model=dict)
async def get_build(
    build_id: str,
    db: Session = Depends(get_db)
):
    """Get build details"""
    build = db.get(JenkinsBuild, build_id)

    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    return build.to_dict()


@router.get("/builds/{build_id}/console", response_model=dict)
async def get_build_console(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    Get build console output

    This is equivalent to the Jenkins console output view
    """
    console_output = await jenkins_service.get_build_console_output(db, build_id)

    if console_output is None:
        raise HTTPException(status_code=404, detail="Build not found")

    return {
        "build_id": build_id,
        "console_output": console_output
    }


@router.post("/builds/{build_id}/abort", response_model=dict)
async def abort_build(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    Abort a running build

    This is equivalent to clicking "Abort" in Jenkins
    """
    success = await jenkins_service.abort_build(db, build_id)

    if not success:
        raise HTTPException(status_code=400, detail="Build cannot be aborted (not running or not found)")

    return {
        "message": "Build aborted successfully in Jenkins",
        "build_id": build_id
    }


# =============================================================================
# Statistics and Monitoring
# =============================================================================

@router.get("/stats", response_model=dict)
async def get_jenkins_stats(
    db: Session = Depends(get_db)
):
    """
    Get Jenkins controller statistics

    This provides an overview similar to Jenkins dashboard
    """
    # Job statistics
    total_jobs = db.execute(select(JenkinsJob)).scalars().all()
    enabled_jobs = [j for j in total_jobs if j.enabled]

    # Build statistics
    all_builds = db.execute(select(JenkinsBuild)).scalars().all()

    running_builds = [b for b in all_builds if b.status == BuildStatus.RUNNING]
    queued_builds = [b for b in all_builds if b.status in [BuildStatus.QUEUED, BuildStatus.PENDING]]

    recent_builds = db.execute(
        select(JenkinsBuild).order_by(desc(JenkinsBuild.created_at)).limit(10)
    ).scalars().all()

    # Success rate
    completed_builds = [b for b in all_builds if b.status in [BuildStatus.SUCCESS, BuildStatus.FAILURE]]
    successful_builds = [b for b in completed_builds if b.status == BuildStatus.SUCCESS]

    return {
        "jobs": {
            "total": len(total_jobs),
            "enabled": len(enabled_jobs),
            "disabled": len(total_jobs) - len(enabled_jobs)
        },
        "builds": {
            "total": len(all_builds),
            "running": len(running_builds),
            "queued": len(queued_builds),
            "success_rate": round(len(successful_builds) / len(completed_builds) * 100, 2) if completed_builds else 0
        },
        "recent_builds": [b.to_dict() for b in recent_builds],
        "running_builds": [b.to_dict() for b in running_builds],
        "queued_builds": [b.to_dict() for b in queued_builds]
    }


@router.get("/queue/stats", response_model=dict)
async def get_queue_stats():
    """
    Get detailed queue and executor statistics

    This provides insights into the Jenkins queue system
    """
    return await jenkins_service.get_queue_stats()


# =============================================================================
# Jenkins Sync Operations
# =============================================================================

@router.post("/sync/jobs", response_model=dict)
async def sync_jobs_from_jenkins(
    db: Session = Depends(get_db)
):
    """
    Sync all jobs from Jenkins to local database

    This is useful for importing existing Jenkins jobs
    """
    try:
        jobs = await jenkins_service.sync_all_jobs(db)

        return {
            "message": f"Synced {len(jobs)} jobs from Jenkins",
            "jobs": jobs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync jobs: {str(e)}")


@router.post("/sync/job/{job_name}", response_model=dict)
async def sync_job_from_jenkins(
    job_name: str,
    db: Session = Depends(get_db)
):
    """
    Sync a specific job from Jenkins to local database
    """
    try:
        job = await jenkins_service.sync_job_from_jenkins(db, job_name)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_name}' not found in Jenkins")

        return {
            "message": f"Job '{job_name}' synced from Jenkins",
            "job": job
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync job: {str(e)}")


@router.get("/connection/status", response_model=dict)
async def check_jenkins_connection():
    """
    Check connection status to Jenkins server
    """
    try:
        is_connected = await jenkins_service.verify_connection()

        return {
            "connected": is_connected,
            "jenkins_url": settings.JENKINS_URL,
            "message": "Connected to Jenkins" if is_connected else "Failed to connect to Jenkins"
        }

    except Exception as e:
        return {
            "connected": False,
            "jenkins_url": settings.JENKINS_URL,
            "message": f"Connection error: {str(e)}"
        }
