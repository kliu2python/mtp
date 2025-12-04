"""API endpoints for browsing Mantis issues stored in a SQLite database."""
from fastapi import APIRouter, HTTPException, Query

from app.services.mantis_service import mantis_service

router = APIRouter()


@router.get("/", summary="List Mantis issues")
async def list_mantis_issues(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=200, description="Items per page"),
    search: str | None = Query(None, description="Search in summary, description, category or issue_id"),
    status: str | None = Query(None, description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    severity: str | None = Query(None, description="Filter by severity"),
    category: str | None = Query(None, description="Filter by category"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_order: str | None = Query("desc", description="asc or desc"),
):
    try:
        issues, total = mantis_service.list_issues(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            priority=priority,
            severity=severity,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "issues": issues,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{issue_id}", summary="Get a specific Mantis issue")
async def get_mantis_issue(issue_id: int):
    try:
        issue = mantis_service.get_issue(issue_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    return issue
