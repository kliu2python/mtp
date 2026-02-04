"""
Jenkins API endpoints
"""
from fastapi import APIRouter, Request, HTTPException
import uuid
import threading
import time

from app.services.jenkins_service import jenkins_service, extract_job_path, JenkinsService
from app.services.mongodb import MongoDBAPI
from app.services.logger import get_logger

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
