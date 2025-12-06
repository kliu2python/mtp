"""
Jenkins API service for triggering and monitoring Jenkins jobs
"""
from datetime import datetime
import logging
import re
import requests
from requests.auth import HTTPBasicAuth
import threading
from time import sleep
import urllib.parse

import jenkins

from app.services.mongodb import MongoDBAPI
from app.core.config import settings

logger = logging.getLogger(__name__)

JENKINS_IP = settings.JENKINS_URL
JENKINS_UN = settings.JENKINS_USERNAME
JENKINS_PW = settings.JENKINS_API_TOKEN
JOB_PATH = settings.JOB_PATH


def extract_job_path(full_url: str) -> str:
    """Convert full Jenkins job URL to job path used by Jenkins API."""
    parsed = urllib.parse.urlparse(full_url)
    segments = parsed.path.strip('/').split('/')
    # Keep only job names (skip the 'job' keywords)
    job_parts = [segments[i + 1] for i in range(0, len(segments), 2) if
                 segments[i] == 'job']
    return '/'.join(job_parts)


class JenkinsService:
    def __init__(
        self,
        server_ip=JENKINS_IP,
        server_un=JENKINS_UN,
        server_pw=JENKINS_PW
        ):
        self.server = jenkins.Jenkins(
            server_ip, username=server_un, password=server_pw
        )
        self.base_job_path = extract_job_path(server_ip)
        self.mongo_client = MongoDBAPI()
        try:
            self.version = self.server.get_version()
            logger.info("Connected to Jenkins version: %s", self.version)
        except Exception as e:
            logger.error("Error connecting to Jenkins: %s", e)
            exit(1)

    def _get_build_status(self, job_path, build_number):
        normalized_job = self._normalize_job_name(job_path)
        build_details = self.server.get_build_info(normalized_job, build_number)
        if build_details.get("building"):
            status = "BUILDING"
        else:
            status = build_details.get("result") or "UNKNOWN"
        return {
            "build_number": build_number,
            "build_status": status,
            "allure_url": "{}allure".format(build_details.get("url")),
        }

    def fetch_auth_info_by_job_name(self, job_name):
        job_info = self.mongo_client.get_job_by_name(job_name)
        return job_info

    def _normalize_job_name(self, job_path: str) -> str:
        """Return a job name relative to the configured Jenkins base path."""
        normalized = (extract_job_path(job_path)
                      if (job_path.startswith("http") or "job/" in job_path)
                      else job_path.strip('/'))

        if self.base_job_path:
            prefix = f"{self.base_job_path.strip('/')}/"
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]

        return normalized

    def _build_job(self, job_path: str, parameters: dict):
        normalized_job = self._normalize_job_name(job_path)
        return self.server.build_job(normalized_job, parameters)

    def get_all_saved_jobs(self):
        res = self.mongo_client.get_all_jobs()
        return res

    def delete_saved_jobs(self, name):
        job_info = self.get_one_saved_job(name)
        group_name = job_info["documents"][0].get("group")
        res = self.mongo_client.delete_job_by_name(name)
        self.mongo_client.update_groups(group_name, append=False)
        return res

    def get_one_saved_job(self, name):
        res = self.mongo_client.get_job_by_name(f"name={name}")
        return res

    def get_job_parameters(self, job_path: str):
        """
        Fetches parameter definitions from a Jenkins job, if it is parameterized
        :param job_path: Full Jenkins job path
        :return: List of parameters (name, default, type, description)
        """
        try:
            normalized_job = self._normalize_job_name(job_path)
            job_info = self.server.get_job_info(normalized_job)
            parameters = []
            if job_info.get("property"):
                for prop in job_info.get("property", []):
                    param_defs = prop.get("parameterDefinitions")
                    if param_defs:
                        for param in param_defs:
                            tmp_type = param.get("_class") or param.get("type")
                            parameters.append({
                                "name": param.get("name"),
                                "type": tmp_type,
                                "default": param.get("defaultParameterValue",
                                                     {}).get("value"),
                                "description": param.get("description", "")})
            else:
                parameters = self.get_job_parameters_via_property(normalized_job)
            if parameters:
                logger.info("Fetched %d parameters for job %s", len(parameters),
                            normalized_job)
            else:
                logger.info("Job %s has no parameters", normalized_job)
            return parameters
        except jenkins.NotFoundException:
            logger.error("Job not found: %s", normalized_job)
        except Exception as e:
            logger.error("Failed to fetch parameters for job %s: %s", normalized_job,
                         e)
        return []

    @classmethod
    def get_job_parameters_via_property(cls, job_path: str):
        """
        Fetches job parameters from the `property` array
        """
        normalized_job = (extract_job_path(job_path)
                          if (job_path.startswith("http") or "job/" in job_path)
                          else job_path.strip("/"))
        base_job_path = extract_job_path(JENKINS_IP)
        if base_job_path:
            prefix = f"{base_job_path.strip('/')}/"
            if normalized_job.startswith(prefix):
                normalized_job = normalized_job[len(prefix):]

        segments = [f"job/{part}" for part in normalized_job.split("/")]
        url = f"{JENKINS_IP}/{'/'.join(segments)}/api/json"

        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(JENKINS_UN, JENKINS_PW)
            )
            response.raise_for_status()
            data = response.json()
            tmp = "hudson.model.ParametersDefinitionProperty"

            for prop in data.get("property", []):
                if prop.get("_class") == tmp:
                    param_defs = prop.get("parameterDefinitions", [])
                    return [
                        {
                            "name": p.get("name"),
                            "type": p.get("type"),
                            "default": p.get(
                                "defaultParameterValue", {}
                            ).get("value"),
                            "description": p.get("description", ""),
                            "choices": p.get("choices", [])
                        } for p in param_defs]
            logger.info("No parameters found for job %s", normalized_job)
            return []

        except Exception as e:
            logger.error(
                "Error fetching job parameters from property for job %s: %s",
                normalized_job, e)
            return []

    def execute_job(self, body):
        job_name = self._normalize_job_name(body.get("server_ip"))
        parameters = body.get("parameters")
        build_num = self._build_job(job_name, parameters)

        # Background worker function
        def update_build_info():
            while True:
                queue_info = self.server.get_queue_item(build_num)
                if 'executable' in queue_info:
                    build_url = queue_info['executable']['url']
                    build_number = queue_info['executable']['number']
                    job_info = self.get_one_saved_job(body.get("job_name"))
                    job_info["documents"][0]["parameters"] = parameters
                    job_info["documents"][0]["job_name"] = body.get("job_name")
                    builds = job_info["documents"][0].get("builds", {})
                    builds[build_num] = {
                        "build_num": build_number,
                        "build_url": build_url,
                        "res": "running"
                    }
                    job_info["documents"][0]["builds"] = builds
                    self.mongo_client.update_document(
                        job_info,
                        db_filter=f"name={body.get('job_name')}"
                    )
                    logger.info(f'saved the docs {job_info}')
                    break
                sleep(2)

        # Launch background thread
        threading.Thread(target=update_build_info, daemon=True).start()

        return True

    def fetch_build_res_using_build_num(self, job_path, build_number, job_name):
        """
        SUCCESS	    Build completed successfully
        FAILURE	    Build failed
        ABORTED	    Build was manually aborted
        UNSTABLE	Build succeeded but had test failures or unstable results
        NOT_BUILT	Build was never run (e.g. skipped)
        null	    Build is still running (not yet completed)
        """
        if not job_name or job_name in [
            'undefined', 'null', ''] or not build_number or build_number in [
            'undefined', 'null', '']:
            logger.warning(
                f"Skipping invalid job_name={job_name},"
                f" build_number={build_number}")
            return
        db_res = self.mongo_client.get_res_of_build_number(job_name,
                                                           build_number)
        if db_res in ["SUCCESS", "ABORTED", "FAILURE", "UNSTABLE", "NOT_BUILT"]:
            logger.info(f"fetch the res {db_res} from db")
            return db_res
        build_info = self.server.get_build_info(job_path, build_number)
        result = build_info.get('result')
        logger.info(f"the res of build {build_number} of job {job_path} is"
                    f" {result}")

        if not result:
            return "Running"
        if result:
            self.mongo_client.update_jenkins_build_res(result, job_name,
                                                       build_number)

        return result

    def fetch_run_details(self, app="ftm_ios"):
        """
        SUCCESS	    Build completed successfully
        FAILURE	    Build failed
        ABORTED	    Build was manually aborted
        UNSTABLE	Build succeeded but had test failures or unstable results
        NOT_BUILT	Build was never run (e.g. skipped)
        null	    Build is still running (not yet completed)
        """
        run_details = self.mongo_client.get_all_run_results(app)
        res_dict = {}
        for db_res in run_details:
            if db_res.get("res") in [
                "SUCCESS", "ABORTED", "FAILURE", "UNSTABLE", "NOT_BUILT"
            ]:
                logger.info(f"fetch the res {db_res} from db")
                break
            job_path = extract_job_path(db_res.get("build_url"))
            match = re.search(r'/(\d+)/?$', db_res.get("build_url"))
            build_number = match.group(1)
            build_info = self.server.get_build_info(job_path, build_number)
            result = build_info.get('result')
            logger.info(f"the res of build {build_number} of job {job_path} is"
                        f" {result}")

            if not result:
                return "running"
            if result:
                self.mongo_client.update_jenkins_run_res(
                    result,
                    db_res.get("name"),
                    datetime.utcnow().isoformat()
                )
            res_dict[db_res.get("name")] = result

        run_details = self.mongo_client.get_all_run_results(app)
        return run_details

    def fetch_run_res_using_build_num(self, job_name=None):
        """
        SUCCESS	    Build completed successfully
        FAILURE	    Build failed
        ABORTED	    Build was manually aborted
        UNSTABLE	Build succeeded but had test failures or unstable results
        NOT_BUILT	Build was never run (e.g. skipped)
        null	    Build is still running (not yet completed)
        """
        if not job_name or job_name in ['undefined', 'null', '']:
            logger.warning(f"Skipping invalid job_name={job_name}")
            return
        db_res = self.mongo_client.get_run_result(job_name)
        if db_res.get("res") in [
            "SUCCESS", "ABORTED", "FAILURE", "UNSTABLE", "NOT_BUILT"
        ]:
            logger.info(f"fetch the res {db_res} from db")
            return db_res
        job_path = extract_job_path(db_res.get("build_url"))
        match = re.search(r'/(\d+)/?$', db_res.get("build_url"))
        build_number = match.group(1)
        build_info = self.server.get_build_info(job_path, build_number)
        result = build_info.get('result')
        logger.info(f"the res of build {build_number} of job {job_path} is"
                    f" {result}")

        if not result:
            return "running"
        if result:
            self.mongo_client.update_jenkins_run_res(
                    result,
                    db_res.get("name"),
                    datetime.utcnow().isoformat()
            )

        return result

    def delete_run_result(self, job_name=None):
        if not job_name or job_name in ['undefined', 'null', '']:
            logger.warning(f"Skipping invalid job_name={job_name}")
            return
        db_res = self.mongo_client.get_run_result(job_name)
        if db_res.get("res") in ["running"]:
            logger.info(f"the test is still running")
            self.fetch_run_res_using_build_num(job_name)
            return
        self.mongo_client.delete_job_by_name(job_name, collection="runner")

    def execute_job_task(self, job_name: str, parameters: dict, udid: str):
        """
        Executes a Jenkins build with the given job name and parameters.
        Also saves the execution record into MongoDB using the provided
        udid as the primary key.
        """
        try:
            normalized_job = self._normalize_job_name(job_name)
            self._build_job(normalized_job, parameters=parameters)
            logger.info("Executed job %s with parameters %s", job_name,
                        parameters)
            record = {
                "_id": udid,  # Use the udid as the primary key.
                "job_name": job_name,
                "parameters": parameters,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            if self.mongo_client:
                self.mongo_client.insert_document(record)
                logger.info("Saved execution record to MongoDB with udid: %s",
                            udid)
            else:
                logger.error(
                    "MongoDB client not initialized; record not saved.")
            return True
        except Exception as e:
            logger.error("Error executing job %s: %s", job_name, e)
            return False

    def execute_run_task(self, data: dict):
        """
        Executes Jenkins builds concurrently for each platform using threads.
        Saves execution records to MongoDB.
        """
        test_env = data.get("environment", "").lower()
        test_platforms = data.get("platforms", [])
        request_info = data.get("parameters", {})
        custom_env = data.get("custom", {})
        test_project = data.get("project", "ftm_ios")

        try:
            test_env_info = self.mongo_client.fetch_test_env_info(test_env,
                                                                  custom_env)
            logger.info("Starting Jenkins run task", extra={
                "project": test_project,
                "environment": test_env,
                "platforms": test_platforms,
                "parameters": request_info,
                "custom_env": custom_env,
            })
            logger.info(f"test env is {test_env_info}")
            threads = []

            for platform in test_platforms:
                test_server = JOB_PATH.get(platform)
                if not test_server:
                    logger.warning("No Jenkins job configured for platform %s",
                                   platform)
                    continue

                # Merge dictionaries
                parameters = {**request_info, **test_env_info}
                parameters.pop("_id", None)
                parameters.pop("name", None)
                logger.info(
                    "Triggering Jenkins job", extra={
                        "platform": platform,
                        "job_path": test_server,
                        "parameters": parameters,
                    })

                def run_and_track(server, params, platform_name):
                    logger.debug(
                        "Thread started for platform %s with params %s",
                        platform_name, params,
                    )
                    build_num = self._build_job(server, params)
                    logger.info(
                        "Queued Jenkins build", extra={
                            "platform": platform_name,
                            "job_path": server,
                            "queue_id": build_num,
                        })

                    while True:
                        queue_info = self.server.get_queue_item(build_num)
                        logger.debug(
                            "Polling queue for platform %s: %s",
                            platform_name, queue_info,
                        )
                        if 'executable' in queue_info:
                            build_url = queue_info['executable']['url']
                            build_number = queue_info['executable']['number']
                            job_info = platform_name + str(build_number)

                            insert_body = {
                                "name": job_info,
                                "build_url": build_url,
                                "build_parameters": params,
                                "platform": platform_name,
                                "app": test_project,
                                "res": "running",
                                "started_at": datetime.utcnow().isoformat(),
                                "updated_at": datetime.utcnow().isoformat()
                            }
                            self.mongo_client.insert_document(
                                insert_body,
                                collection="runner"
                            )
                            if params.get("test_scope") == "acceptable":
                                acceptable_record = {
                                    **insert_body,
                                    "test_scope": "acceptable",
                                }
                                acceptable_result = (
                                    self.mongo_client.insert_acceptable_test_record(
                                        acceptable_record
                                    )
                                )
                                if acceptable_result is None:
                                    logger.error(
                                        "Failed to persist acceptable test record for %s",
                                        job_info,
                                    )
                                else:
                                    logger.info(
                                        "Persisted acceptable test record for %s", job_info
                                    )
                            logger.info(
                                "Saved Jenkins run record", extra={
                                    "job": job_info,
                                    "build_number": build_number,
                                    "build_url": build_url,
                                    "platform": platform_name,
                                })
                            break
                        sleep(2)

                thread = threading.Thread(
                    target=run_and_track,
                    args=(test_server, parameters.copy(), platform),
                    daemon=True)
                threads.append(thread)
                logger.debug(
                    "Starting thread for platform %s", platform)
                thread.start()

            return True

        except Exception as e:
            logger.exception("Failed to execute job")
            return False

    def fetch_job_structure(self, data):
        job_path = data.get('server_ip')
        job_name = data.get('job_name')
        server_un = data.get("server_un")
        server_pw = data.get("server_pw")
        job_tags = data.get("tags")
        job_group = data.get("group")
        api_url = f"{job_path.rstrip('/')}/api/json"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            tmp_target = "hudson.model.ParametersDefinitionProperty"
            for prop in data.get("property", []):
                if prop.get("_class") == tmp_target:
                    res = [
                        {"name": p.get("name"),
                         "type": p.get("type"),
                         "default": p.get("defaultParameterValue", {}).get("value"),
                         "description": p.get("description", ""),
                         "choices": p.get("choices", [])} for p in
                        prop.get("parameterDefinitions", [])]
                    record = {
                        "name": job_name,
                        "server_ip": job_path,
                        "server_un": server_un,
                        "server_pw": server_pw,
                        "tags": job_tags,
                        "group": job_group,
                        "parameters": res
                    }
                    self.mongo_client.update_document(
                        record,  db_filter=f"name={job_name}"
                    )
                    self.mongo_client.update_groups(job_group)
                    return res

            return []  # no parameters defined
        except Exception as e:
            print(f"Failed to fetch parameters: {e}")
            return []

# Create singleton instance
jenkins_service = JenkinsService()
