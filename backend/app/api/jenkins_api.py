"""
Jenkins API endpoints
"""
from fastapi import APIRouter, Request

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
        records = runner.refresh_acceptable_test_records(records)
        sorted_records = sorted(
            records,
            key=lambda item: item.get("updated_at") or item.get("started_at") or "",
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
    record_id = request.query_params.get("id") or request.query_params.get("record_id")
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