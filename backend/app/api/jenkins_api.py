"""
Jenkins API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
import logging
from app.core.database import get_db
from app.services.jenkins_service import jenkins_service
from app.services.settings_service import platform_settings_service
from app.schemas.jenkins import (
    JenkinsJobTrigger,
    JenkinsJobInfo,
    JenkinsJobList,
    JenkinsTriggerResponse,
    JenkinsBuildStatus,
    JenkinsBuildConsole,
    JenkinsStopBuildResponse,
    JenkinsJobParameter
)
from fastapi import Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


def _configure_jenkins(db: Session, overrides: Optional[Dict[str, str]] = None):
    settings = platform_settings_service.get_settings(db)
    overrides = overrides or {}

    jenkins_service.configure(
        overrides.get("jenkins_url") or settings.jenkins_url or "",
        overrides.get("username") or settings.jenkins_username or "",
        overrides.get("api_token") or settings.jenkins_api_token or "",
    )
    return settings


@router.get("/jobs", response_model=List[JenkinsJobList])
async def get_all_jenkins_jobs(db: Session = Depends(get_db)):
    """
    Get all available Jenkins jobs

    Returns:
        List of Jenkins jobs with basic information
    """
    try:
        _configure_jenkins(db)
        jobs = jenkins_service.get_all_jobs()
        return jobs
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting Jenkins jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Jenkins jobs: {str(e)}"
        )


@router.get("/jobs/{job_name}", response_model=JenkinsJobInfo)
async def get_jenkins_job_info(job_name: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific Jenkins job

    Args:
        job_name: Name of the Jenkins job

    Returns:
        Detailed job information
    """
    try:
        _configure_jenkins(db)
        job_info = jenkins_service.get_job_info(job_name)
        return job_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting job info for {job_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_name}' not found or error occurred: {str(e)}"
        )


@router.post("/jobs/trigger", response_model=JenkinsTriggerResponse)
async def trigger_jenkins_job(job_trigger: JenkinsJobTrigger, db: Session = Depends(get_db)):
    """
    Trigger a Jenkins job with optional parameters

    Args:
        job_trigger: Job name and optional parameters

    Returns:
        Trigger response with job and queue information
    """
    try:
        _configure_jenkins(
            db,
            {
                "jenkins_url": job_trigger.jenkins_url,
                "username": job_trigger.username,
                "api_token": job_trigger.api_token,
            },
        )
        result = jenkins_service.trigger_job(
            job_name=job_trigger.job_name,
            parameters=job_trigger.parameters
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error triggering job {job_trigger.job_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger job: {str(e)}"
        )


@router.get("/jobs/{job_name}/builds/{build_number}", response_model=JenkinsBuildStatus)
async def get_build_status(job_name: str, build_number: int, db: Session = Depends(get_db)):
    """
    Get status of a specific build

    Args:
        job_name: Name of the Jenkins job
        build_number: Build number

    Returns:
        Build status information
    """
    try:
        _configure_jenkins(db)
        build_status = jenkins_service.get_build_status(job_name, build_number)
        return build_status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting build status for {job_name} #{build_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build not found or error occurred: {str(e)}"
        )


@router.get("/jobs/{job_name}/builds/{build_number}/console", response_model=JenkinsBuildConsole)
async def get_build_console(job_name: str, build_number: int, db: Session = Depends(get_db)):
    """
    Get console output of a specific build

    Args:
        job_name: Name of the Jenkins job
        build_number: Build number

    Returns:
        Console output
    """
    try:
        _configure_jenkins(db)
        console_output = jenkins_service.get_build_console_output(job_name, build_number)
        return {
            "job_name": job_name,
            "build_number": build_number,
            "console_output": console_output
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting console output for {job_name} #{build_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build console not found or error occurred: {str(e)}"
        )


@router.post("/jobs/{job_name}/builds/{build_number}/stop", response_model=JenkinsStopBuildResponse)
async def stop_jenkins_build(job_name: str, build_number: int, db: Session = Depends(get_db)):
    """
    Stop a running build

    Args:
        job_name: Name of the Jenkins job
        build_number: Build number to stop

    Returns:
        Stop operation result
    """
    try:
        _configure_jenkins(db)
        result = jenkins_service.stop_build(job_name, build_number)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error stopping build {job_name} #{build_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop build: {str(e)}"
        )


@router.get("/jobs/{job_name}/parameters", response_model=List[JenkinsJobParameter])
async def get_job_parameters(job_name: str, db: Session = Depends(get_db)):
    """
    Get parameters defined for a job

    Args:
        job_name: Name of the Jenkins job

    Returns:
        List of parameter definitions
    """
    try:
        _configure_jenkins(db)
        parameters = jenkins_service.get_job_parameters(job_name)
        return parameters
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting parameters for job {job_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found or error occurred: {str(e)}"
        )
