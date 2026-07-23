"""
Jobs router: CRUD + control endpoints for scraping jobs.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.job_store import job_store
from app.schemas import APIResponse

router = APIRouter()


@router.get("", summary="List all jobs")
async def list_jobs(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> APIResponse:
    """Retrieve all scraping jobs with optional filtering."""
    try:
        jobs = job_store.list_all(status=status, type_=type)
        total = len(jobs)
        sliced_jobs = jobs[offset: offset + limit]

        return APIResponse(success=True, message="OK", data={
            "jobs": sliced_jobs,
            "total": total,
            "limit": limit,
            "offset": offset,
        })
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@router.get("/stats", summary="Dashboard statistics")
async def get_stats() -> APIResponse:
    """Aggregate statistics for the dashboard."""
    try:
        stats = job_store.get_stats()
        return APIResponse(success=True, message="OK", data=stats)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@router.get("/{job_id}", summary="Get job details")
async def get_job(job_id: str) -> APIResponse:
    """Get detailed status for a specific job."""
    try:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return APIResponse(success=True, message="OK", data=job)
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@router.post("/{job_id}/cancel", summary="Cancel a job")
async def cancel_job(job_id: str) -> APIResponse:
    """Cancel a queued or running job."""
    try:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_store.set_status(job_id, "cancelled")
        
        # Cancel the task reference if it exists in scrape router
        from app.routers.scrape import _running_tasks
        task = _running_tasks.get(job_id)
        if task:
            task.cancel()
            
        return APIResponse(success=True, message="Job cancelled.", data={"job_id": job_id})
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@router.post("/{job_id}/pause", summary="Pause a running job")
async def pause_job(job_id: str) -> APIResponse:
    """Pause a running job."""
    try:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job_store.set_status(job_id, "paused")
        return APIResponse(success=True, message="Job paused.", data={"job_id": job_id})
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@router.post("/{job_id}/resume", summary="Resume a paused job")
async def resume_job(job_id: str) -> APIResponse:
    """Resume a paused job."""
    try:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job_store.set_status(job_id, "running")
        return APIResponse(success=True, message="Job resumed.", data={"job_id": job_id})
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@router.delete("/{job_id}", summary="Delete a job")
async def delete_job(job_id: str) -> APIResponse:
    """Delete a job and its data."""
    try:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        job_store.delete(job_id)
        return APIResponse(success=True, message="Job deleted.", data={"job_id": job_id})
    except HTTPException:
        raise
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)
