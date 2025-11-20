"""
Jenkins API Client

A client for interacting with Jenkins REST API for job execution and result management.
Connects to the real Jenkins instance at 10.160.13.30:8080.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import quote
import json

logger = logging.getLogger(__name__)


class JenkinsAPIClient:
    """Client for Jenkins REST API"""

    def __init__(
        self,
        base_url: str = "http://10.160.13.30:8080",
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 300
    ):
        """
        Initialize Jenkins API client

        Args:
            base_url: Jenkins server URL
            username: Jenkins username (optional for anonymous access)
            api_token: Jenkins API token (optional for anonymous access)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    def _get_auth(self) -> Optional[aiohttp.BasicAuth]:
        """Get authentication object if credentials are provided"""
        if self.username and self.api_token:
            return aiohttp.BasicAuth(self.username, self.api_token)
        return None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Jenkins API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            json_data: JSON data
            headers: Additional headers

        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.request(
                    method=method,
                    url=url,
                    auth=self._get_auth(),
                    params=params,
                    data=data,
                    json=json_data,
                    headers=headers
                ) as response:
                    response.raise_for_status()

                    # Check if response is JSON
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"text": text, "status": response.status}

            except aiohttp.ClientError as e:
                logger.error(f"Jenkins API request failed: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in Jenkins API request: {e}")
                raise

    # ==================== Job Management ====================

    async def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get list of all jobs

        Returns:
            List of job dictionaries
        """
        result = await self._request('GET', '/api/json', params={'tree': 'jobs[name,url,color,lastBuild[number,timestamp,result]]'})
        return result.get('jobs', [])

    async def get_job(self, job_name: str) -> Dict[str, Any]:
        """
        Get job details

        Args:
            job_name: Name of the job

        Returns:
            Job details dictionary
        """
        encoded_name = quote(job_name, safe='')
        return await self._request('GET', f'/job/{encoded_name}/api/json')

    async def create_job(self, job_name: str, config_xml: str) -> bool:
        """
        Create a new job

        Args:
            job_name: Name of the job to create
            config_xml: Jenkins job configuration XML

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        headers = {'Content-Type': 'application/xml'}
        await self._request(
            'POST',
            f'/createItem',
            params={'name': encoded_name},
            data=config_xml.encode('utf-8'),
            headers=headers
        )
        return True

    async def update_job(self, job_name: str, config_xml: str) -> bool:
        """
        Update existing job configuration

        Args:
            job_name: Name of the job
            config_xml: New Jenkins job configuration XML

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        headers = {'Content-Type': 'application/xml'}
        await self._request(
            'POST',
            f'/job/{encoded_name}/config.xml',
            data=config_xml.encode('utf-8'),
            headers=headers
        )
        return True

    async def delete_job(self, job_name: str) -> bool:
        """
        Delete a job

        Args:
            job_name: Name of the job to delete

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        await self._request('POST', f'/job/{encoded_name}/doDelete')
        return True

    async def enable_job(self, job_name: str) -> bool:
        """
        Enable a job

        Args:
            job_name: Name of the job

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        await self._request('POST', f'/job/{encoded_name}/enable')
        return True

    async def disable_job(self, job_name: str) -> bool:
        """
        Disable a job

        Args:
            job_name: Name of the job

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        await self._request('POST', f'/job/{encoded_name}/disable')
        return True

    # ==================== Build Management ====================

    async def trigger_build(
        self,
        job_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        wait: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger a build

        Args:
            job_name: Name of the job
            parameters: Build parameters (optional)
            wait: Whether to wait for build to be queued

        Returns:
            Dictionary with queue item information
        """
        encoded_name = quote(job_name, safe='')

        if parameters:
            # Trigger parameterized build
            endpoint = f'/job/{encoded_name}/buildWithParameters'
            result = await self._request('POST', endpoint, params=parameters)
        else:
            # Trigger simple build
            endpoint = f'/job/{encoded_name}/build'
            result = await self._request('POST', endpoint)

        if wait:
            # Wait a bit for build to be queued
            await asyncio.sleep(1)

        return result

    async def get_build(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """
        Get build details

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            Build details dictionary
        """
        encoded_name = quote(job_name, safe='')
        return await self._request('GET', f'/job/{encoded_name}/{build_number}/api/json')

    async def get_last_build(self, job_name: str) -> Optional[Dict[str, Any]]:
        """
        Get last build details

        Args:
            job_name: Name of the job

        Returns:
            Build details dictionary or None if no builds
        """
        encoded_name = quote(job_name, safe='')
        try:
            return await self._request('GET', f'/job/{encoded_name}/lastBuild/api/json')
        except:
            return None

    async def get_build_console_output(self, job_name: str, build_number: int) -> str:
        """
        Get build console output

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            Console output as string
        """
        encoded_name = quote(job_name, safe='')
        result = await self._request('GET', f'/job/{encoded_name}/{build_number}/consoleText')
        return result.get('text', '')

    async def get_build_console_output_progressive(
        self,
        job_name: str,
        build_number: int,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Get progressive console output (for streaming)

        Args:
            job_name: Name of the job
            build_number: Build number
            start: Starting byte position

        Returns:
            Dictionary with console text and metadata
        """
        encoded_name = quote(job_name, safe='')
        endpoint = f'/job/{encoded_name}/{build_number}/logText/progressiveText'

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                f"{self.base_url}/{endpoint}",
                auth=self._get_auth(),
                params={'start': start}
            ) as response:
                text = await response.text()
                more_data = response.headers.get('X-More-Data', 'false') == 'true'
                text_size = int(response.headers.get('X-Text-Size', len(text)))

                return {
                    'text': text,
                    'more_data': more_data,
                    'text_size': text_size,
                    'has_more': more_data
                }

    async def stop_build(self, job_name: str, build_number: int) -> bool:
        """
        Stop a running build

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        await self._request('POST', f'/job/{encoded_name}/{build_number}/stop')
        return True

    async def delete_build(self, job_name: str, build_number: int) -> bool:
        """
        Delete a build

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            True if successful
        """
        encoded_name = quote(job_name, safe='')
        await self._request('POST', f'/job/{encoded_name}/{build_number}/doDelete')
        return True

    # ==================== Build History ====================

    async def get_build_history(
        self,
        job_name: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get build history for a job

        Args:
            job_name: Name of the job
            limit: Maximum number of builds to return

        Returns:
            List of build dictionaries
        """
        encoded_name = quote(job_name, safe='')
        tree = 'builds[number,timestamp,result,duration,building,url]'

        if limit:
            tree = f'builds[number,timestamp,result,duration,building,url]{{0,{limit}}}'

        result = await self._request(
            'GET',
            f'/job/{encoded_name}/api/json',
            params={'tree': tree}
        )
        return result.get('builds', [])

    # ==================== Queue Management ====================

    async def get_queue(self) -> List[Dict[str, Any]]:
        """
        Get build queue

        Returns:
            List of queued items
        """
        result = await self._request('GET', '/queue/api/json')
        return result.get('items', [])

    async def get_queue_item(self, item_id: int) -> Dict[str, Any]:
        """
        Get queue item details

        Args:
            item_id: Queue item ID

        Returns:
            Queue item details
        """
        return await self._request('GET', f'/queue/item/{item_id}/api/json')

    async def cancel_queue_item(self, item_id: int) -> bool:
        """
        Cancel a queued build

        Args:
            item_id: Queue item ID

        Returns:
            True if successful
        """
        await self._request('POST', f'/queue/cancelItem', params={'id': item_id})
        return True

    # ==================== Node Management ====================

    async def get_nodes(self) -> List[Dict[str, Any]]:
        """
        Get list of all nodes

        Returns:
            List of node dictionaries
        """
        result = await self._request('GET', '/computer/api/json')
        return result.get('computer', [])

    async def get_node(self, node_name: str) -> Dict[str, Any]:
        """
        Get node details

        Args:
            node_name: Name of the node

        Returns:
            Node details dictionary
        """
        encoded_name = quote(node_name, safe='')
        return await self._request('GET', f'/computer/{encoded_name}/api/json')

    # ==================== Artifacts ====================

    async def get_build_artifacts(
        self,
        job_name: str,
        build_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get build artifacts

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            List of artifact dictionaries
        """
        encoded_name = quote(job_name, safe='')
        result = await self._request(
            'GET',
            f'/job/{encoded_name}/{build_number}/api/json',
            params={'tree': 'artifacts[fileName,relativePath]'}
        )
        return result.get('artifacts', [])

    async def download_artifact(
        self,
        job_name: str,
        build_number: int,
        artifact_path: str
    ) -> bytes:
        """
        Download a build artifact

        Args:
            job_name: Name of the job
            build_number: Build number
            artifact_path: Relative path to artifact

        Returns:
            Artifact content as bytes
        """
        encoded_name = quote(job_name, safe='')
        url = f"{self.base_url}/job/{encoded_name}/{build_number}/artifact/{artifact_path}"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, auth=self._get_auth()) as response:
                response.raise_for_status()
                return await response.read()

    # ==================== Test Results ====================

    async def get_test_results(
        self,
        job_name: str,
        build_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get test results for a build

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            Test results dictionary or None if no tests
        """
        encoded_name = quote(job_name, safe='')
        try:
            return await self._request(
                'GET',
                f'/job/{encoded_name}/{build_number}/testReport/api/json'
            )
        except:
            return None

    # ==================== Utility Methods ====================

    async def verify_connection(self) -> bool:
        """
        Verify connection to Jenkins server

        Returns:
            True if connection is successful
        """
        try:
            await self._request('GET', '/api/json')
            return True
        except:
            return False

    async def get_version(self) -> str:
        """
        Get Jenkins version

        Returns:
            Jenkins version string
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                f"{self.base_url}/api/json",
                auth=self._get_auth()
            ) as response:
                return response.headers.get('X-Jenkins', 'Unknown')
