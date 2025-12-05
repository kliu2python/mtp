"""
Jenkins API endpoints
"""
from fastapi import APIRouter, Request
import logging

from app.services.jenkins_service import jenkins_service, extract_job_path, JenkinsService
from app.services.mongodb import MongoDBAPI

logger = logging.getLogger(__name__)

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
def ExecuteFTMJenkinsTask(request: Request):
    try:
        data = request.json
        res = runner.execute_run_task(data)
        return {"results": res}
    except Exception as e:
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
        records = MongoDBAPI().get_acceptable_test_records()
        sorted_records = sorted(
            records,
            key=lambda item: item.get("updated_at") or item.get("started_at") or "",
            reverse=True,
        )
        return {"results": sorted_records}
    except Exception as exc:
        logger.error("Failed to fetch acceptable test records: %s", exc)
        return {"error": "Error fetching acceptable test records from DB"}, 500


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