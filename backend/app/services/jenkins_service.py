"""
Jenkins API service for triggering and monitoring Jenkins jobs
"""
from datetime import datetime
import re
import requests
from requests.auth import HTTPBasicAuth
import threading
from time import sleep
import urllib.parse
import uuid

import jenkins
import json
import requests
from urllib.parse import urljoin

from app.services.mongodb import MongoDBAPI
from app.core.config import settings
from app.services.logger import get_logger

logger = get_logger()

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

    def _parse_test_case_metadata(self, test_name: str) -> dict:
        """
        Parse additional metadata from test case name.

        Examples:
        - test_fortiautenticator_fortitoken_mfa_push[v7.6.4,build3596,250820 (GA.F) Timezone DB Version: 1.0009 Timezone DB IANA Version: 2025b, 16-ftm-android]
        - test_fortigate_admin_fortitoken_mfa_push[v7.6.4,build3596,250820 (GA.F) Timezone DB Version: 1.0009 Timezone DB IANA Version: 2025b, 16-ftm-android]
        """
        metadata = {
            'test_component': '',  # FTK, FIC, etc.
            'test_platform': '',   # FAC, FGT, etc.
            'os_version': '',      # iOS/Android version
            'device_info': '',     # Device identifier
        }

        if not test_name:
            return metadata

        # Extract test component and platform from the test name prefix
        test_name_lower = test_name.lower()

        # Determine platform (FAC = FortiAuthenticator, FGT = FortiGate)
        # Priority order: explicit prefixes
        if 'fortigate' in test_name_lower or 'admin' in test_name_lower:
            metadata['test_platform'] = 'FGT'  # FortiGate
        elif 'fortiautenticator' in test_name_lower:
            metadata['test_platform'] = 'FAC'  # FortiAuthenticator
        elif 'fortitoken_cloud' in test_name_lower:
            # Special case: cloud tests with "fortigate" should be FGT
            if 'fortigate' in test_name_lower:
                metadata['test_platform'] = 'FGT'  # FortiGate
            else:
                # FortiAuthenticator for pure cloud tests
                metadata['test_platform'] = 'FAC'
        else:
            metadata['test_platform'] = 'Unknown'

        # Determine component (FTK = FortiToken, FIC = FortiToken Cloud)
        # Check for fortitoken_cloud first since it contains 'fortitoken'
        if 'fortitoken_cloud' in test_name_lower:
            metadata['test_component'] = 'FIC'  # FortiToken Cloud
        elif 'fortitoken' in test_name_lower:
            metadata['test_component'] = 'FTK'  # FortiToken
        else:
            metadata['test_component'] = 'Unknown'

        # Extract information from bracketed section [version_info, device_info]
        import re
        bracket_pattern = r'\[([^\]]+)\]'
        match = re.search(bracket_pattern, test_name)
        if match:
            bracket_content = match.group(1)
            # Split by comma to get different parts
            parts = [part.strip() for part in bracket_content.split(',')]

            # Extract OS version and device info from the last part
            if parts:
                # Usually contains device info like "16-ftm-android"
                last_part = parts[-1]
                if '-' in last_part:
                    device_parts = last_part.split('-')
                    if len(device_parts) >= 3:
                        metadata['device_info'] = device_parts[0]  # "16"
                        # "android" or similar
                        metadata['os_version'] = device_parts[2]

        return metadata

    def fetch_allure_report_data(self, allure_url: str):
        """
        Fetch and parse Allure report data from the given URL.

        Args:
            allure_url (str): URL to the Allure report

        Returns:
            dict: Parsed test results data or None if failed
        """
        try:
            # Construct the URL to fetch widgets data which contains summary
            widgets_url = urljoin(allure_url.rstrip(
                '/') + '/', 'data/widgets.json')

            logger.info(f"Fetching Allure report data from: {widgets_url}")
            response = requests.get(widgets_url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract summary statistics
            summary = {}
            for widget in data.get('widgets', []):
                if widget.get('id') == 'summary':
                    summary = widget.get('data', {})
                    break

            # Parse the results
            total = summary.get('total', 0)
            passed = summary.get('passed', 0)
            failed = summary.get('failed', 0)
            broken = summary.get('broken', 0)
            skipped = summary.get('skipped', 0)
            unknown = summary.get('unknown', 0)

            results = {
                'total': total,
                'passed_count': passed,
                'failed_count': failed,
                'broken_count': broken,
                'skipped_count': skipped,
                'unknown_count': unknown,
                'duration': summary.get('time', {}).get('duration', 0) // 1000,
                'start_time': summary.get('time', {}).get('start', None),
                'stop_time': summary.get('time', {}).get('stop', None),
                'test_cases': []  # Initialize test cases array
            }

            # Try to fetch test case details from suites.csv
            try:
                suites_csv_url = urljoin(
                    allure_url.rstrip('/') + '/', 'data/suites.csv')
                logger.info(
                    f"Fetching Allure suites data from: {suites_csv_url}")
                csv_response = requests.get(suites_csv_url, timeout=30)
                if csv_response.status_code == 200:
                    # Parse CSV data
                    import csv
                    from io import StringIO

                    csv_data = StringIO(csv_response.text)
                    reader = csv.DictReader(csv_data)

                    test_cases = []
                    for row in reader:
                        test_case = {
                            'name': row.get('Name', ''),
                            'status': row.get('Status', '').lower(),
                            'duration_ms': int(row.get('Duration in ms', 0)),
                            'parent_suite': row.get('Parent Suite', ''),
                            'suite': row.get('Suite', ''),
                            'sub_suite': row.get('Sub Suite', ''),
                            'test_class': row.get('Test Class', ''),
                            'test_method': row.get('Test Method', ''),
                            'description': row.get('Description', ''),
                            'start_time': row.get('Start Time', ''),
                            'stop_time': row.get('Stop Time', '')
                        }
                        test_cases.append(test_case)

                    results['test_cases'] = test_cases
                    logger.info(
                        f"Successfully extracted {len(test_cases)} test cases from suites.csv")
            except Exception as csv_error:
                logger.warning(
                    f"Could not fetch or parse suites.csv: {csv_error}")
                # This is not critical, so we continue

            logger.info(f"Successfully fetched Allure report data: {results}")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Allure report from {allure_url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(
                f"Error parsing Allure report JSON from {allure_url}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching Allure report from {allure_url}: {e}")
            return None

    def extract_results_from_zip(self, zip_file_path: str):
        """
        Extract test results from a zip file containing test reports.

        Args:
            zip_file_path (str): Path to the zip file containing test results

        Returns:
            dict: Parsed test results data or None if failed
        """
        import zipfile
        import os
        import xml.etree.ElementTree as ET
        import csv

        try:
            logger.info(
                f"Extracting test results from zip file: {zip_file_path}")

            # Check if file exists
            if not os.path.exists(zip_file_path):
                logger.error(f"Zip file not found: {zip_file_path}")
                return None

            results = {
                'total': 0,
                'passed_count': 0,
                'failed_count': 0,
                'skipped_count': 0,
                'duration': 0,
                'test_cases': []  # Store individual test cases
            }

            # Extract and parse reports from ZIP file
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Look for common test result files
                for file_info in zip_ref.filelist:
                    filename = file_info.filename
                    # Handle JUnit XML format
                    if filename.endswith('.xml') and 'test' in filename.lower():
                        with zip_ref.open(filename) as xml_file:
                            try:
                                tree = ET.parse(xml_file)
                                root = tree.getroot()

                                # Parse testsuite elements
                                for testsuite in root.findall('testsuite'):
                                    results['total'] += int(
                                        testsuite.get('tests', 0))
                                    results['passed_count'] += int(
                                        testsuite.get('passes', 0))
                                    results['failed_count'] += int(
                                        testsuite.get('failures', 0))
                                    results['skipped_count'] += int(
                                        testsuite.get('skipped', 0))
                                    results['duration'] += int(
                                        float(testsuite.get('time', 0)))

                                    # Extract individual test cases
                                    for testcase in testsuite.findall('testcase'):
                                        case_data = {
                                            'name': testcase.get('name', ''),
                                            'classname': testcase.get('classname', ''),
                                            'time': float(testcase.get('time', 0)),
                                            'status': 'PASSED'
                                        }

                                        # Check for failure or error elements
                                        if testcase.find('failure') is not None or testcase.find('error') is not None:
                                            case_data['status'] = 'FAILED'
                                            failure = testcase.find(
                                                'failure') or testcase.find('error')
                                            case_data['failure_message'] = failure.get(
                                                'message', '') if failure is not None else ''
                                        elif testcase.find('skipped') is not None:
                                            case_data['status'] = 'SKIPPED'

                                        # Add metadata from test case name
                                        metadata = self._parse_test_case_metadata(
                                            case_data['name'])
                                        case_data.update(metadata)

                                        results['test_cases'].append(case_data)

                                # Handle individual testcase elements if no testsuites
                                if results['total'] == 0:
                                    testcases = root.findall('.//testcase')
                                    results['total'] = len(testcases)

                                    for testcase in testcases:
                                        case_data = {
                                            'name': testcase.get('name', ''),
                                            'classname': testcase.get('classname', ''),
                                            'time': float(testcase.get('time', 0)),
                                            'status': 'PASSED'
                                        }

                                        # Check for failure or error elements
                                        if testcase.find('failure') is not None or testcase.find('error') is not None:
                                            case_data['status'] = 'FAILED'
                                            failure = testcase.find(
                                                'failure') or testcase.find('error')
                                            case_data['failure_message'] = failure.get(
                                                'message', '') if failure is not None else ''
                                            results['failed_count'] += 1
                                        elif testcase.find('skipped') is not None:
                                            case_data['status'] = 'SKIPPED'
                                            results['skipped_count'] += 1
                                        else:
                                            results['passed_count'] += 1

                                        # Add metadata from test case name
                                        metadata = self._parse_test_case_metadata(
                                            case_data['name'])
                                        case_data.update(metadata)

                                        results['test_cases'].append(case_data)

                            except ET.ParseError as e:
                                logger.warning(
                                    f"Could not parse XML file {filename}: {e}")
                                continue

                    # Handle Allure JSON format if present
                    elif filename.endswith('.json') and 'allure' in filename.lower():
                        with zip_ref.open(filename) as json_file:
                            try:
                                import json
                                data = json.load(json_file)

                                # Extract results from Allure JSON format
                                # This is a simplified implementation - would need to be expanded based on actual format
                                if isinstance(data, dict) and 'statistic' in data:
                                    stats = data['statistic']
                                    results['total'] += stats.get('total', 0)
                                    results['passed_count'] += stats.get(
                                        'passed', 0)
                                    results['failed_count'] += stats.get(
                                        'failed', 0)
                                    results['skipped_count'] += stats.get(
                                        'skipped', 0)

                                    # If this is a test case result, add it to test_cases
                                    if 'name' in data:
                                        case_data = {
                                            'name': data.get('name', ''),
                                            'status': 'UNKNOWN',
                                            'time': data.get('time', 0)
                                        }

                                        # Determine status from statistic if available
                                        if stats.get('failed', 0) > 0:
                                            case_data['status'] = 'FAILED'
                                        elif stats.get('passed', 0) > 0:
                                            case_data['status'] = 'PASSED'
                                        elif stats.get('skipped', 0) > 0:
                                            case_data['status'] = 'SKIPPED'

                                        # Add metadata from test case name
                                        metadata = self._parse_test_case_metadata(
                                            case_data['name'])
                                        case_data.update(metadata)

                                        results['test_cases'].append(case_data)

                            except json.JSONDecodeError as e:
                                logger.warning(
                                    f"Could not parse JSON file {filename}: {e}")
                                continue

                    # Handle Allure suites.csv file if present
                    elif filename.endswith('suites.csv') and 'allure-report' in filename.replace('\\', '/').lower():
                        try:
                            with zip_ref.open(filename) as csv_file:
                                # Decode bytes to string
                                csv_content = csv_file.read().decode('utf-8')
                                from io import StringIO

                                csv_data = StringIO(csv_content)
                                reader = csv.DictReader(csv_data)

                                # Clear previously extracted test cases and use CSV data instead
                                results['test_cases'] = []

                                for row in reader:
                                    # Parse additional metadata from test case name
                                    test_name = row.get('Name', '')
                                    metadata = self._parse_test_case_metadata(
                                        test_name)

                                    test_case = {
                                        'name': test_name,
                                        'status': row.get('Status', '').lower(),
                                        'duration_ms': int(row.get('Duration in ms', 0)),
                                        'parent_suite': row.get('Parent Suite', ''),
                                        'suite': row.get('Suite', ''),
                                        'sub_suite': row.get('Sub Suite', ''),
                                        'test_class': row.get('Test Class', ''),
                                        'test_method': row.get('Test Method', ''),
                                        'description': row.get('Description', ''),
                                        'start_time': row.get('Start Time', ''),
                                        'stop_time': row.get('Stop Time', ''),
                                        **metadata
                                    }
                                    results['test_cases'].append(test_case)

                                # Update summary counts based on CSV data
                                results['total'] = len(results['test_cases'])
                                results['passed_count'] = sum(
                                    1 for tc in results['test_cases'] if tc['status'] == 'passed')
                                results['failed_count'] = sum(
                                    1 for tc in results['test_cases'] if tc['status'] == 'failed')
                                results['skipped_count'] = sum(
                                    1 for tc in results['test_cases'] if tc['status'] == 'skipped')

                                # Count broken tests as failed since they indicate issues
                                broken_count = sum(
                                    1 for tc in results['test_cases'] if tc['status'] == 'broken')
                                results['failed_count'] += broken_count

                                logger.info(
                                    f"Successfully extracted {len(results['test_cases'])} test cases from suites.csv")

                        except Exception as csv_error:
                            logger.warning(
                                f"Could not parse suites.csv file {filename}: {csv_error}")
                            continue

            logger.info(
                f"Successfully extracted results from zip file: {results}")
            return results

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file {zip_file_path}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Error extracting results from zip file {zip_file_path}: {e}")
            return None

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
                parameters = self.get_job_parameters_via_property(
                    normalized_job)
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

    def refresh_acceptable_test_result(self, record: dict):
        """Fetch Jenkins result for an acceptable test and persist it."""
        if not record or not record.get("build_url"):
            return record

        if record.get("res") in ["SUCCESS", "ABORTED", "FAILURE", "UNSTABLE", "NOT_BUILT"]:
            return record

        job_path = extract_job_path(record.get("build_url"))
        match = re.search(r'/(\d+)/?$', record.get("build_url", ""))
        if not match:
            logger.warning(
                "Unable to determine build number from %s", record.get("build_url"))
            return record

        build_number = match.group(1)
        try:
            # Add timeout to prevent hanging requests
            build_info = self.server.get_build_info(job_path, int(build_number), depth=0)
            result = build_info.get('result')
        except jenkins.TimeoutException:
            logger.warning("Timeout fetching Jenkins result for %s #%s",
                         job_path, build_number)
            return record
        except jenkins.JenkinsException as exc:
            logger.warning("Jenkins error fetching result for %s #%s: %s",
                         job_path, build_number, exc)
            return record
        except Exception as exc:
            logger.error("Failed to fetch Jenkins result for %s #%s: %s",
                         job_path, build_number, exc)
            return record

        if not result:
            return {**record, "res": record.get("res") or "running"}

        updates = {
            "res": result,
            "updated_at": datetime.utcnow().isoformat(),
        }
        try:
            self.mongo_client.update_acceptable_test_record(
                record.get("_id") or record.get("name"), updates)
            record.update(updates)
        except Exception as exc:
            logger.error("Failed to update acceptable test record %s: %s",
                         record.get("name"), exc)
        return record

    def refresh_acceptable_test_records(self, records: list):
        """Refresh Jenkins results for acceptable test records."""
        refreshed = []
        for record in records or []:
            try:
                refreshed.append(self.refresh_acceptable_test_result(record))
            except Exception as exc:
                logger.error(
                    "Failed to refresh acceptable test record %s: %s", record.get('name') if isinstance(record, dict) else record, exc)
                refreshed.append(record)
        return refreshed

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
        test_scope = data.get("test_scope", "acceptable")

        # Handle template saving
        save_as_template = custom_env.get("save_as_template", False)
        template_name = custom_env.get("template_name")

        if save_as_template and template_name:
            try:
                # Create template document
                template_doc = {
                    "id": str(uuid.uuid4()),
                    "name": template_name,
                    "platform": request_info.get("platform"),
                    "test_scope": request_info.get("test_scope"),
                    "test_product": request_info.get("test_product"),
                    "environment": test_env,
                    "device_type": request_info.get("device_type"),
                    "timeout": request_info.get("timeout", 3600),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                # Save template to MongoDB
                self.mongo_client.insert_document(
                    template_doc, collection="test_templates")
                logger.info(f"Saved test template: {template_name}")
            except Exception as e:
                logger.error(f"Failed to save test template: {e}")

        try:
            try:
                test_env_info = self.mongo_client.fetch_test_env_info(test_env,
                                                                      custom_env)
                logger.info(f"test env is {test_env_info}")
            except Exception as e:
                logger.error(f"Failed to fetch test environment info: {e}")
                # If we can't fetch environment info, continue with empty dict
                test_env_info = {}

            logger.info("Starting Jenkins run task", extra={
                "project": test_project,
                "environment": test_env,
                "platforms": test_platforms,
                "parameters": request_info,
                "custom_env": custom_env,
            })
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

                            stored_params = {
                                key: value
                                for key, value in params.items()
                                if key not in {"mantis_ids", "build_number", "app_download_url", "download_url"}
                            }

                            insert_body = {
                                "name": job_info,
                                "build_url": build_url,
                                "build_parameters": stored_params,
                                "platform": platform_name,
                                "app": test_project,
                                "res": "running",
                                "build_number": params.get("build_number"),
                                "resolved_mantis_ids": params.get("mantis_ids"),
                                "download_url": params.get("app_download_url") or params.get("download_url"),
                                "app_file": params.get("ftm_ipa_version") or params.get("ftm_apk_version"),
                                "started_at": datetime.utcnow().isoformat(),
                                "updated_at": datetime.utcnow().isoformat()
                            }
                            self.mongo_client.insert_document(
                                insert_body,
                                collection="runner"
                            )
                            logger.info(f"{test_scope} is {params}")
                            if test_scope == "acceptable":
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
