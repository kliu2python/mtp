"""
AI Analysis API endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ai_analyzer import create_analyzer, LogType
from app.services.settings_service import platform_settings_service

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeLogsRequest(BaseModel):
    """Request to analyze logs"""
    logs: str
    log_type: str = "generic"  # fgt, fac, pytest, generic
    test_name: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    provider: Optional[str] = None  # claude, openai, ollama
    model: Optional[str] = None


class SuggestFixesRequest(BaseModel):
    """Request for fix suggestions"""
    error_message: str
    context: Optional[dict] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class CompareTestRunsRequest(BaseModel):
    """Request to compare test runs"""
    previous_log: str
    current_log: str
    test_name: str
    provider: Optional[str] = None
    model: Optional[str] = None


def _build_analyzer(
    db: Session,
    provider: Optional[str],
    model: Optional[str],
):
    settings = platform_settings_service.get_settings(db)
    resolved_provider = provider or settings.ai_provider or "claude"
    resolved_model = model or settings.ai_model
    analyzer = create_analyzer(
        provider=resolved_provider,
        api_key=settings.ai_api_key,
        model=resolved_model,
        base_url=settings.ai_base_url,
    )
    return analyzer, resolved_provider, resolved_model


@router.post("/analyze-logs")
async def analyze_logs(request: AnalyzeLogsRequest, db: Session = Depends(get_db)):
    """
    Analyze logs using AI

    Supports multiple log types (FGT, FAC, pytest) and AI providers
    """
    try:
        # Create analyzer
        analyzer, resolved_provider, resolved_model = _build_analyzer(
            db=db,
            provider=request.provider,
            model=request.model,
        )

        # Validate log type
        try:
            log_type = LogType(request.log_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid log type. Must be one of: {', '.join([t.value for t in LogType])}"
            )

        # Analyze logs
        result = analyzer.analyze_logs(
            logs=request.logs,
            log_type=log_type,
            test_name=request.test_name,
            focus_areas=request.focus_areas
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze logs: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/suggest-fixes")
async def suggest_fixes(request: SuggestFixesRequest, db: Session = Depends(get_db)):
    """
    Get AI-powered fix suggestions for an error

    Provides actionable recommendations to resolve issues
    """
    try:
        # Create analyzer
        analyzer, resolved_provider, resolved_model = _build_analyzer(
            db=db,
            provider=request.provider,
            model=request.model,
        )

        # Get suggestions
        suggestions = analyzer.suggest_fixes(
            error_message=request.error_message,
            context=request.context
        )

        return {
            "success": True,
            "provider": resolved_provider,
            "model": resolved_model or analyzer.model,
            "error_message": request.error_message,
            "suggestions": suggestions
        }

    except Exception as e:
        logger.error(f"Failed to get fix suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.post("/compare-runs")
async def compare_test_runs(request: CompareTestRunsRequest, db: Session = Depends(get_db)):
    """
    Compare two test runs and identify changes

    Identifies regressions, improvements, and changes between runs
    """
    try:
        # Create analyzer
        analyzer, resolved_provider, resolved_model = _build_analyzer(
            db=db,
            provider=request.provider,
            model=request.model,
        )

        # Compare runs
        result = analyzer.compare_test_runs(
            previous_log=request.previous_log,
            current_log=request.current_log,
            test_name=request.test_name
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Comparison failed"))

        result.update({
            "provider": resolved_provider,
            "model": resolved_model or analyzer.model,
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare test runs: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/providers")
async def list_providers():
    """
    List available AI providers and their capabilities

    Returns information about supported providers
    """
    return {
        "providers": [
            {
                "name": "claude",
                "display_name": "Anthropic Claude",
                "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
                "default_model": "claude-3-5-sonnet-20241022",
                "requires_api_key": True
            },
            {
                "name": "openai",
                "display_name": "OpenAI GPT",
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                "default_model": "gpt-4o",
                "requires_api_key": True
            },
            {
                "name": "ollama",
                "display_name": "Ollama (Local)",
                "models": ["llama3.1", "llama2", "mistral", "codellama"],
                "default_model": "llama3.1",
                "requires_api_key": False,
                "note": "Requires local Ollama server running"
            }
        ],
        "log_types": [
            {
                "name": "fgt",
                "display_name": "FortiGate Logs",
                "description": "Mobile application logs from FortiGate"
            },
            {
                "name": "fac",
                "display_name": "FortiAuthenticator Logs",
                "description": "Mobile application logs from FortiAuthenticator"
            },
            {
                "name": "pytest",
                "display_name": "Pytest Logs",
                "description": "Pytest automation test execution logs"
            },
            {
                "name": "generic",
                "display_name": "Generic Logs",
                "description": "General application or system logs"
            }
        ]
    }


@router.post("/test/{test_id}/analyze")
async def analyze_test_logs(
    test_id: str,
    provider: str = "claude",
    model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Analyze logs from a specific test execution

    Automatically fetches logs from the test record and analyzes them
    """
    try:
        # TODO: Fetch test logs from database
        # This would integrate with your test execution system
        # For now, return a placeholder

        raise HTTPException(
            status_code=501,
            detail="Test log analysis integration coming soon. Use /analyze-logs endpoint with logs directly."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze test logs: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
