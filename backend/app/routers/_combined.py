"""
Results, Exports, and Logs routers.
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os

from app.config import settings
from app.schemas import APIResponse, ExportFormat
from app.job_store import job_store

results_router = APIRouter()
exports_router = APIRouter()
logs_router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────
@results_router.get("/{job_id}", summary="Get job results")
async def get_results(job_id: str) -> APIResponse:
    """Get the scraped results for a completed job."""
    try:
        data = job_store.get_result(job_id)
        if not data:
            return APIResponse(success=False, message="Results not found. Job may still be running.", data=None)
        return APIResponse(success=True, message="OK", data=data)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


# ─────────────────────────────────────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────────────────────────────────────
@exports_router.post("", summary="Export job results")
async def create_export(
    job_id: str = Query(...),
    format: ExportFormat = Query(ExportFormat.JSON),
    include_logs: bool = Query(False),
    custom_name: Optional[str] = Query(None, description="Optional custom filename prefix (no extension)"),
) -> APIResponse:
    """Export job results in the specified format."""
    try:
        from app.services.export_service import ExportService
        import re
        from urllib.parse import urlparse

        data = job_store.get_result(job_id)
        if not data:
            return APIResponse(success=False, message="No results found for this job.", data=None)

        job = job_store.get(job_id) or {}
        job_type = job.get("type", "data")
        url = job.get("target_url", "")

        # ── Filename resolution ────────────────────────────────────────────
        if custom_name and custom_name.strip():
            # User supplied a custom name — sanitize and use it directly
            name = re.sub(r'[^a-zA-Z0-9_\-]', '_', custom_name.strip())
            name = re.sub(r'_+', '_', name).strip('_') or "scraped_export"
        else:
            # Auto-detect: try to get a descriptive entity name from the results
            entity_name = None
            if isinstance(data, dict):
                if data.get("name"):
                    entity_name = data["name"]
                elif data.get("username"):
                    entity_name = data["username"]
                elif isinstance(data.get("profile"), dict) and data["profile"].get("username"):
                    entity_name = data["profile"]["username"]
                elif data.get("domain"):
                    entity_name = data["domain"]
                elif data.get("profile_name"):
                    entity_name = data["profile_name"]
                elif data.get("title"):
                    entity_name = data["title"]
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                first = data[0]
                entity_name = first.get("domain") or first.get("username") or None

            if entity_name:
                name = str(entity_name)
            else:
                # Fall back to domain extracted from target_url
                if url.startswith("http://") or url.startswith("https://") or "www." in url or "/" in url:
                    try:
                        temp_url = url if "://" in url else f"http://{url}"
                        parsed = urlparse(temp_url)
                        name = parsed.netloc or parsed.path
                        if name.startswith("www."):
                            name = name[4:]
                    except Exception:
                        name = url
                else:
                    name = url

            # Sanitize auto-detected name
            name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
            name = re.sub(r'_+', '_', name).strip('_')
            if not name:
                name = "scraped_export"

        ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{name}_{job_type}_{ts}"


        if format == ExportFormat.JSON:
            fp = ExportService.export_json(data, f"{filename_base}.json")
        elif format == ExportFormat.CSV:
            # Flatten to list of pages or reviews
            rows = data.get("pages", data.get("reviews", [data])) if isinstance(data, dict) else [data]
            fp = ExportService.export_csv(rows, f"{filename_base}.csv")
        elif format == ExportFormat.EXCEL:
            sheets = {"Results": data.get("pages", [data]) if isinstance(data, dict) else [data]}
            fp = ExportService.export_excel(sheets, f"{filename_base}.xlsx")
        elif format == ExportFormat.XML:
            fp = ExportService.export_xml(data, filename=f"{filename_base}.xml")
        elif format == ExportFormat.PDF:
            fp = ExportService.export_pdf(
                data if isinstance(data, dict) else {"data": data},
                title=f"Job {job_id} Export",
                filename=f"{filename_base}.pdf"
            )
        elif format == ExportFormat.ZIP:
            # Create JSON + CSV, then ZIP both
            json_fp = ExportService.export_json(data, f"{filename_base}.json")
            rows = data.get("pages", [data]) if isinstance(data, dict) else [data]
            csv_fp = ExportService.export_csv(rows, f"{filename_base}.csv")
            fp = ExportService.export_zip([json_fp, csv_fp], f"{filename_base}.zip")
        else:
            return APIResponse(success=False, message="Unsupported format.", data=None)

        return APIResponse(success=True, message="Export created.", data={
            "file": os.path.basename(fp),
            "path": fp,
            "size": ExportService.get_file_size(fp),
            "format": format,
        })
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@exports_router.get("/download/{filename}", summary="Download export file")
async def download_export(filename: str) -> FileResponse:
    """Download a previously created export file."""
    filepath = os.path.join(settings.EXPORT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(filepath, filename=filename)


@exports_router.get("", summary="List all exports")
async def list_exports() -> APIResponse:
    """List all export files."""
    try:
        files = []
        for fname in os.listdir(settings.EXPORT_DIR):
            fp = os.path.join(settings.EXPORT_DIR, fname)
            files.append({
                "filename": fname,
                "size": os.path.getsize(fp),
                "created_at": os.path.getctime(fp),
            })
        files.sort(key=lambda x: x["created_at"], reverse=True)
        return APIResponse(success=True, message="OK", data=files)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@exports_router.delete("/clear", summary="Clear export history")
async def clear_exports() -> APIResponse:
    """Clear all exported files."""
    try:
        count = 0
        for fname in os.listdir(settings.EXPORT_DIR):
            fp = os.path.join(settings.EXPORT_DIR, fname)
            if os.path.isfile(fp):
                os.remove(fp)
                count += 1
        return APIResponse(success=True, message=f"Export history cleared. Deleted {count} files.", data=None)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


# ─────────────────────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────────────────────
@logs_router.get("/{job_id}", summary="Get logs for a job")
async def get_logs(
    job_id: str,
    level: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
) -> APIResponse:
    """Get structured log entries for a job."""
    try:
        logs = job_store.get_logs(job_id, level=level, limit=limit)
        return APIResponse(success=True, message="OK", data=logs)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)


@logs_router.get("", summary="Get all recent logs")
async def get_all_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100),
) -> APIResponse:
    """Get recent logs across all jobs."""
    try:
        logs = job_store.get_all_logs(level=level, limit=limit)
        return APIResponse(success=True, message="OK", data=logs)
    except Exception as e:
        return APIResponse(success=False, message=str(e), data=None)
