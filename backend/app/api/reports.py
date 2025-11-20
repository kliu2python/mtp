"""Reports API - Fetch Allure reports, artifacts, and logs from builds"""
import os
import logging
import tempfile
import zipfile
import shutil
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io

from app.core.database import get_db
from app.models.jenkins_build import JenkinsBuild
from app.models.jenkins_node import JenkinsNode
from app.services.ssh_session import SSHSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def fetch_file_from_node(
    node: JenkinsNode,
    remote_path: str,
    local_path: str
) -> bool:
    """
    Fetch a file from a Jenkins node via SSH/SCP

    Args:
        node: JenkinsNode to fetch from
        remote_path: Path to file on remote node
        local_path: Local path to save file

    Returns:
        True if successful, False otherwise
    """
    try:
        ssh = SSHSession(
            hostname=node.host,
            port=node.port,
            username=node.username,
            password=node.password,
            ssh_key_path=node.ssh_key
        )

        # Connect
        if not ssh.connect():
            logger.error(f"Failed to connect to node {node.name}")
            return False

        # Use SCP to fetch file
        # Check if file exists first
        check_cmd = f"test -f {remote_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
        exit_code, output, error = ssh.execute_command(check_cmd, timeout=5)

        if "NOT_FOUND" in output:
            logger.warning(f"File {remote_path} not found on node {node.name}")
            ssh.disconnect()
            return False

        # Create local directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Use cat to stream file content
        read_cmd = f"cat {remote_path}"
        exit_code, output, error = ssh.execute_command(read_cmd, timeout=30)

        if exit_code == 0:
            with open(local_path, 'w') as f:
                f.write(output)
            logger.info(f"Fetched {remote_path} from {node.name} to {local_path}")
            ssh.disconnect()
            return True
        else:
            logger.error(f"Failed to read {remote_path}: {error}")
            ssh.disconnect()
            return False

    except Exception as e:
        logger.error(f"Error fetching file from node: {e}")
        return False


async def fetch_directory_as_zip(
    node: JenkinsNode,
    remote_dir: str,
    output_zip_path: str
) -> bool:
    """
    Fetch an entire directory from a Jenkins node as a ZIP file

    Args:
        node: JenkinsNode to fetch from
        remote_dir: Directory path on remote node
        output_zip_path: Local path to save ZIP file

    Returns:
        True if successful, False otherwise
    """
    try:
        ssh = SSHSession(
            hostname=node.host,
            port=node.port,
            username=node.username,
            password=node.password,
            ssh_key_path=node.ssh_key
        )

        # Connect
        if not ssh.connect():
            logger.error(f"Failed to connect to node {node.name}")
            return False

        # Create ZIP on remote node
        remote_zip = f"{remote_dir}.zip"
        zip_cmd = f"cd {os.path.dirname(remote_dir)} && zip -r {remote_zip} {os.path.basename(remote_dir)}"
        exit_code, output, error = ssh.execute_command(zip_cmd, timeout=60)

        if exit_code != 0:
            logger.error(f"Failed to create ZIP on node: {error}")
            ssh.disconnect()
            return False

        # Stream ZIP file content
        read_cmd = f"cat {remote_zip} | base64"
        exit_code, output, error = ssh.execute_command(read_cmd, timeout=120)

        if exit_code == 0:
            # Decode base64 and write to file
            import base64
            zip_content = base64.b64decode(output)
            with open(output_zip_path, 'wb') as f:
                f.write(zip_content)

            # Cleanup remote ZIP
            cleanup_cmd = f"rm -f {remote_zip}"
            ssh.execute_command(cleanup_cmd, timeout=5)

            logger.info(f"Fetched directory {remote_dir} from {node.name} as ZIP")
            ssh.disconnect()
            return True
        else:
            logger.error(f"Failed to read ZIP file: {error}")
            ssh.disconnect()
            return False

    except Exception as e:
        logger.error(f"Error fetching directory from node: {e}")
        return False


@router.get("/builds/{build_id}/allure-results")
async def download_allure_results(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    Download Allure results for a build as a ZIP file
    """
    build = db.get(JenkinsBuild, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if not build.allure_results_path:
        raise HTTPException(status_code=404, detail="No Allure results available for this build")

    if not build.node_id:
        raise HTTPException(status_code=400, detail="Build has no associated node")

    node = db.get(JenkinsNode, build.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Create temp file for ZIP
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        zip_path = tmp.name

    try:
        success = await fetch_directory_as_zip(
            node,
            build.allure_results_path,
            zip_path
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to fetch Allure results from node")

        # Return ZIP file
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"allure-results-{build.job_name}-{build.build_number}.zip",
            background=lambda: os.unlink(zip_path)  # Cleanup after send
        )

    except Exception as e:
        # Cleanup on error
        if os.path.exists(zip_path):
            os.unlink(zip_path)
        raise HTTPException(status_code=500, detail=f"Error downloading results: {str(e)}")


@router.get("/builds/{build_id}/artifacts")
async def list_artifacts(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    List all artifacts for a build
    """
    build = db.get(JenkinsBuild, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    return {
        "build_id": str(build.id),
        "job_name": build.job_name,
        "build_number": build.build_number,
        "artifacts": build.artifacts,
        "allure_results_path": build.allure_results_path,
        "screenshots_path": build.screenshots_path,
        "logs_path": build.logs_path
    }


@router.get("/builds/{build_id}/artifacts/download")
async def download_artifact(
    build_id: str,
    artifact_path: str,
    db: Session = Depends(get_db)
):
    """
    Download a specific artifact from a build

    Query params:
        artifact_path: Path to the artifact on the node
    """
    build = db.get(JenkinsBuild, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if not build.node_id:
        raise HTTPException(status_code=400, detail="Build has no associated node")

    node = db.get(JenkinsNode, build.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Security check: ensure artifact_path is in allowed paths
    allowed_paths = [
        build.allure_results_path,
        build.screenshots_path,
        build.logs_path
    ]
    allowed_paths.extend(build.artifacts)

    # Check if artifact_path starts with any allowed path
    is_allowed = any(
        artifact_path.startswith(str(allowed))
        for allowed in allowed_paths if allowed
    )

    if not is_allowed:
        raise HTTPException(status_code=403, detail="Access to this artifact is not allowed")

    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        local_path = tmp.name

    try:
        success = await fetch_file_from_node(node, artifact_path, local_path)

        if not success:
            raise HTTPException(status_code=404, detail="Artifact not found on node")

        # Determine content type based on file extension
        content_types = {
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.html': 'text/html',
            '.txt': 'text/plain',
            '.log': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }

        ext = os.path.splitext(artifact_path)[1].lower()
        content_type = content_types.get(ext, 'application/octet-stream')

        return FileResponse(
            local_path,
            media_type=content_type,
            filename=os.path.basename(artifact_path),
            background=lambda: os.unlink(local_path)
        )

    except Exception as e:
        if os.path.exists(local_path):
            os.unlink(local_path)
        raise HTTPException(status_code=500, detail=f"Error downloading artifact: {str(e)}")


@router.get("/builds/{build_id}/screenshots")
async def download_screenshots(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    Download screenshots for a build as a ZIP file
    """
    build = db.get(JenkinsBuild, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if not build.screenshots_path:
        raise HTTPException(status_code=404, detail="No screenshots available for this build")

    if not build.node_id:
        raise HTTPException(status_code=400, detail="Build has no associated node")

    node = db.get(JenkinsNode, build.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        zip_path = tmp.name

    try:
        success = await fetch_directory_as_zip(node, build.screenshots_path, zip_path)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to fetch screenshots from node")

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"screenshots-{build.job_name}-{build.build_number}.zip",
            background=lambda: os.unlink(zip_path)
        )

    except Exception as e:
        if os.path.exists(zip_path):
            os.unlink(zip_path)
        raise HTTPException(status_code=500, detail=f"Error downloading screenshots: {str(e)}")


@router.get("/builds/{build_id}/logs")
async def download_logs(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    Download logs for a build as a ZIP file
    """
    build = db.get(JenkinsBuild, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if not build.logs_path:
        raise HTTPException(status_code=404, detail="No logs available for this build")

    if not build.node_id:
        raise HTTPException(status_code=400, detail="Build has no associated node")

    node = db.get(JenkinsNode, build.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        zip_path = tmp.name

    try:
        success = await fetch_directory_as_zip(node, build.logs_path, zip_path)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to fetch logs from node")

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"logs-{build.job_name}-{build.build_number}.zip",
            background=lambda: os.unlink(zip_path)
        )

    except Exception as e:
        if os.path.exists(zip_path):
            os.unlink(zip_path)
        raise HTTPException(status_code=500, detail=f"Error downloading logs: {str(e)}")


@router.get("/builds/{build_id}/generate-report")
async def generate_allure_report(
    build_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate and serve Allure HTML report for a build
    NOTE: Requires Allure CLI to be installed on the backend server
    """
    build = db.get(JenkinsBuild, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if not build.allure_results_path:
        raise HTTPException(status_code=404, detail="No Allure results available for this build")

    if not build.node_id:
        raise HTTPException(status_code=400, detail="Build has no associated node")

    node = db.get(JenkinsNode, build.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Create temp directories
    results_dir = tempfile.mkdtemp(prefix='allure-results-')
    report_dir = tempfile.mkdtemp(prefix='allure-report-')
    zip_path = tempfile.mktemp(suffix='.zip')

    try:
        # First fetch the results directory
        results_zip = tempfile.mktemp(suffix='.zip')
        success = await fetch_directory_as_zip(node, build.allure_results_path, results_zip)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to fetch Allure results from node")

        # Extract results
        with zipfile.ZipFile(results_zip, 'r') as zip_ref:
            zip_ref.extractall(results_dir)
        os.unlink(results_zip)

        # Generate Allure report
        import subprocess
        cmd = ['allure', 'generate', results_dir, '-o', report_dir, '--clean']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            logger.error(f"Allure generate failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate Allure report. Is Allure CLI installed? Error: {result.stderr}"
            )

        # Zip the report
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', report_dir)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"allure-report-{build.job_name}-{build.build_number}.zip",
            background=lambda: [
                shutil.rmtree(results_dir, ignore_errors=True),
                shutil.rmtree(report_dir, ignore_errors=True),
                os.unlink(zip_path) if os.path.exists(zip_path) else None
            ]
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Allure report generation timed out")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Allure CLI not found. Please install: pip install allure-pytest or download from https://github.com/allure-framework/allure2/releases"
        )
    except Exception as e:
        # Cleanup
        shutil.rmtree(results_dir, ignore_errors=True)
        shutil.rmtree(report_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.unlink(zip_path)
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
