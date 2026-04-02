"""
Jenkins API endpoints
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from sqlalchemy.orm import Session
import uuid
import threading
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.jenkins_service import jenkins_service, extract_job_path, JenkinsService, get_jenkins_job_status_manager
from app.services.mongodb import MongoDBAPI
from app.services.logger import get_logger
from app.core.database import get_db

logger = get_logger()

router = APIRouter()
runner = jenkins_service


def fetch_auth_info_by_job_name(job_name):
    job_info = MongoDBAPI().get_job_by_name(f"name={job_name}")
    return job_info.get("documents")[0]


@router.post("/execute/job")
def ExecuteJobsByName(request: Request):
    data = request.get_json()
    parts = data.get('server_ip').split('/')
    server_ip = f"{parts[0]}//{parts[2]}"
    try:
        results = JenkinsService(
            server_ip,
            data.get('server_un'),
            data.get('server_pw')
        ).execute_job(data)
    except Exception:
        return "auth failed", 500
    return results, 200


@router.get("/jobs")
def ListAllSavedJobs():
    results = runner.get_all_saved_jobs()
    return results, 200


@router.delete("/jobs/<string:job_name>")
def DeleteJobByName(job_name):
    results = runner.delete_saved_jobs(job_name)
    return results, 200


@router.get("/jobs/<string:job_name>")
def GetOneSavedJob(job_name):
    results = runner.get_one_saved_job(job_name)
    return results, 200


@router.get("/jobs/build/result")
def GetJobBuildResultByBuildNumber(request: Request):
    job_name = request.args.get("job_name")
    build_num = request.args.get("build_number")
    job_info = fetch_auth_info_by_job_name(job_name)
    if not job_info:
        return f"no job {job_name} found", 500
    parts = job_info.get('server_ip').split('/')
    server_ip = f"{parts[0]}//{parts[2]}"
    job_path = extract_job_path(job_info.get('server_ip'))
    try:
        results = JenkinsService(
            server_ip, job_info.get('server_un'), job_info.get('server_pw')
        ).fetch_build_res_using_build_num(job_path, build_num, job_name)
    except Exception:
        return "auth failed", 500
    return results, 200


@router.post("/jobs/parameters")
def AuthAndParameterCheck(request: Request):
    data = request.json
    parts = data.get('server_ip').split('/')
    server_ip = f"{parts[0]}//{parts[2]}"
    try:
        results = JenkinsService(server_ip,
                                 data.get('server_un'),
                                 data.get('server_pw')
                                 ).fetch_job_structure(data)
    except Exception:
        return "auth failed", 500

    return {"results": results}


@router.get("/db_jobs")
def ListAllJobsFromDB():
    """
    Returns a list of all jobs from the MongoDB database using MongoDBAPI.
    """
    try:
        # Fetch the jobs from the MongoDB using the MongoDBAPI client
        jobs = MongoDBAPI().get_all_jobs()
        return {"results": jobs}
    except Exception as e:
        return {"error": "Error fetching job structure on DB"}, 500


@router.get("/groups")
def ListAllGroups():
    """
    Returns a list of all jobs from the MongoDB database using MongoDBAPI.
    """
    try:
        # Fetch the jobs from the MongoDB using the MongoDBAPI client
        jobs = MongoDBAPI().get_all_groups()
        return {"results": jobs}
    except Exception as e:
        return {"error": "Error fetching job structure on DB"}, 500


@router.post("/run/execute/ftm")
async def ExecuteFTMJenkinsTask(request: Request):
    try:
        data = await request.json()
        logger.info("Received FTM run request: %s", data)
        res = runner.execute_run_task(data)
        logger.info("FTM run request processed with result: %s", res)
        return {"results": res}
    except Exception as e:
        logger.exception("Failed to execute FTM Jenkins task")
        return {"error": "Error fetching job structure on DB"}, 500


@router.post("/tests/run-template")
async def RunTestFromTemplate(request: Request):
    """Run a test using a saved template"""
    try:
        data = await request.json()
        template_id = data.get("template_id")
        vm_id = data.get("vm_id")

        if not template_id:
            raise HTTPException(
                status_code=400, detail="Template ID is required")

        # Fetch template from MongoDB
        template = MongoDBAPI().get_test_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Prepare test data using template
        test_data = {
            "environment": template.get("environment", "qa"),
            "platforms": [template.get("platform")],
            "parameters": {
                "platform": template.get("platform"),
                "test_scope": template.get("test_scope"),
                "test_product": template.get("test_product"),
                "device_type": template.get("device_type"),
                "timeout": template.get("timeout", 3600),
            },
            "project": template.get("platform") == "ios" and "ftm_ios" or "ftm_android",
        }

        # Execute the test
        res = runner.execute_run_task(test_data)
        logger.info("Template-based test execution started: %s", res)
        return {"results": res}
    except Exception as e:
        logger.exception("Failed to run test from template")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run/ios/ftm")
def GetFTMIOSTaskRun():
    try:
        results = MongoDBAPI().get_all_run_results("ftm_ios")
    except Exception:
        return "auth failed", 500
    return results, 200


@router.get("/run/acceptable-tests")
def GetAcceptableTestRecords():
    """Return acceptable-scope test records persisted in MongoDB."""
    try:
        mongo_client = MongoDBAPI()
        records = mongo_client.get_acceptable_test_records()

        # Refresh records with timeout to prevent gateway timeout
        refreshed_records = records  # Default to original records
        refresh_exception = None

        def refresh_worker():
            nonlocal refreshed_records, refresh_exception
            try:
                refreshed_records = runner.refresh_acceptable_test_records(records)
            except Exception as exc:
                refresh_exception = exc

        # Create and start refresh thread
        refresh_thread = threading.Thread(target=refresh_worker)
        refresh_thread.daemon = True
        refresh_thread.start()

        # Wait for completion with timeout (30 seconds)
        refresh_thread.join(timeout=30)

        # If thread is still alive, it timed out
        if refresh_thread.is_alive():
            logger.warning("Refreshing acceptable test records timed out, returning possibly stale data")
        elif refresh_exception:
            logger.warning("Error refreshing acceptable test records: %s", refresh_exception)
        else:
            records = refreshed_records

        sorted_records = sorted(
            records,
            key=lambda item: item.get(
                "updated_at") or item.get("started_at") or "",
            reverse=True,
        )
        logger.info(
            "Returning %d acceptable test records", len(sorted_records)
        )
        return {"results": sorted_records}
    except Exception as exc:
        logger.error("Failed to fetch acceptable test records: %s", exc)
        return {"error": "Error fetching acceptable test records from DB"}, 500


@router.delete("/run/acceptable-tests")
def DeleteAcceptableTestRecord(request: Request):
    """Remove an acceptable test record by _id or name."""
    record_id = request.query_params.get(
        "id") or request.query_params.get("record_id")
    name = request.query_params.get("name")

    if not record_id and not name:
        return {"error": "record identifier is required"}, 400

    try:
        result = MongoDBAPI().delete_acceptable_test_record(record_id=record_id, name=name)
        if result is None:
            return {"error": "Unable to delete acceptable test record"}, 500

        return {"result": "deleted"}
    except Exception as exc:
        logger.error("Failed to delete acceptable test record: %s", exc)
        return {"error": "Error deleting acceptable test record"}, 500


@router.get("/run/results/ios/ftm")
def GetFTMIOSTaskRunResults():
    try:
        results = runner.fetch_run_details()
    except Exception:
        return "auth failed", 500
    return results, 200


@router.get("/run/result/ios/ftm")
def GetFTMIOSTaskRunResult(request: Request):
    try:
        job_name = request.args.get("job_name")
        results = runner.fetch_run_res_using_build_num(job_name)
    except Exception:
        return "auth failed", 500
    return results, 200


@router.delete("/run/result/ios/ftm/delete")
def DeleteFTMiOSResult(request: Request):
    try:
        job_name = request.args.get("job_name")
        results = runner.delete_run_result(job_name)
    except Exception:
        return "auth failed", 500
    return results, 200


# =============================================================================
# Jenkins Job Status Management APIs
# =============================================================================

@router.get("/job-status/status")
def get_job_status(
    job_url: str = Query(..., description="Jenkins Job URL"),
    timestamp: Optional[str] = Query(None, description="ISO format timestamp for comparison"),
    db: Session = Depends(get_db)
):
    """
    Get Jenkins Job status.

    - **job_url**: Jenkins Job URL
    - **timestamp**: Reference timestamp for status comparison (ISO format)

    Status descriptions:
    - **running**: A build is currently executing
    - **completed**: Last completed build time >= parameter timestamp
    - **pending**: Last completed build time < parameter timestamp (not started yet)
    """
    try:
        manager = get_jenkins_job_status_manager(db)

        # Parse timestamp
        parameter_timestamp = None
        if timestamp:
            try:
                parameter_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")

        # Get status (without refresh)
        job_url_normalized = job_url.rstrip('/') + '/'
        status_record = manager.get_status(job_url_normalized)

        if not status_record:
            raise HTTPException(status_code=404, detail="Job status not found")

        status_record['status_description'] = _get_status_description(status_record.get('computed_status'))
        return status_record

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/job-status/update")
def update_job_status(
    job_url: str = Query(..., description="Jenkins Job URL"),
    job_name: Optional[str] = Query(None, description="Job name"),
    timestamp: Optional[str] = Query(None, description="ISO format timestamp for comparison"),
    db: Session = Depends(get_db)
):
    """
    Update job status from Jenkins.

    - **job_url**: Jenkins Job URL
    - **job_name**: Job name (optional)
    - **timestamp**: Reference timestamp for status comparison (ISO format)

    This endpoint will:
    1. Connect to Jenkins server to fetch latest status
    2. Update database record
    3. Compute and return status
    """
    try:
        manager = get_jenkins_job_status_manager(db)

        # Parse timestamp
        parameter_timestamp = None
        if timestamp:
            try:
                parameter_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")

        # Extract job name if not provided
        if not job_name:
            job_name = job_url.split('/')[-2] if job_url.strip('/').endswith('/') else job_url.split('/')[-1]

        # Update status
        result = manager.update_status_from_jenkins(job_name, job_url, parameter_timestamp)
        result['status_description'] = _get_status_description(result.get('computed_status'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update job status: {str(e)}")


@router.get("/job-status/list")
def list_job_statuses(
    status: Optional[str] = Query(None, description="Filter by status (running, completed, pending)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Limit results"),
    db: Session = Depends(get_db)
):
    """
    List all job statuses.

    - **status**: Filter by status (running, completed, pending)
    - **limit**: Limit number of results
    """
    try:
        manager = get_jenkins_job_status_manager(db)
        return manager.list_statuses(status_filter=status, limit=limit)
    except Exception as e:
        logger.error(f"Error listing job statuses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list job statuses: {str(e)}")


@router.delete("/job-status/delete")
def delete_job_status(
    job_url: str = Query(..., description="Jenkins Job URL"),
    db: Session = Depends(get_db)
):
    """
    Delete a job status record.

    - **job_url**: Jenkins Job URL
    """
    try:
        manager = get_jenkins_job_status_manager(db)

        if manager.delete_status(job_url):
            return {"message": "Job status deleted successfully", "job_url": job_url}
        else:
            raise HTTPException(status_code=404, detail="Job status not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete job status: {str(e)}")


@router.post("/job-status/refresh-all")
def refresh_all_job_statuses(db: Session = Depends(get_db)):
    """
    Refresh all job statuses.

    This endpoint iterates through all recorded job URLs and fetches
    the latest status from Jenkins.
    """
    try:
        manager = get_jenkins_job_status_manager(db)
        count = manager.refresh_all_statuses()

        return {
            "message": f"Refreshed {count} job status record(s)",
            "count": count
        }

    except Exception as e:
        logger.error(f"Error refreshing all job statuses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh job statuses: {str(e)}")


@router.get("/job-status/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    """
    try:
        jenkins_version = jenkins_service.version

        return {
            "status": "healthy",
            "jenkins_connected": True,
            "jenkins_version": jenkins_version,
            "database_connected": True
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def _get_status_description(status: Optional[str]) -> str:
    """
    Get status description.

    Args:
        status: Status value

    Returns:
        str: Status description
    """
    descriptions = {
        'running': 'A build is currently executing',
        'completed': 'Last completed build finished',
        'pending': 'Build has not started yet',
    }
    return descriptions.get(status, 'Unknown status') if status else 'Unknown status'
