"""REST endpoints for authenticated script upload and execution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from mechatronics3.server.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])

_MAX_UPLOAD_BYTES = 1_048_576  # 1 MiB

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FileInfo(BaseModel):
    name: str
    size: int


class ExecuteRequest(BaseModel):
    filename: str
    timeout: Annotated[int, Field(ge=1, le=300)] = 30


class ExecuteResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _upload_dir(request: Request) -> Path:
    return request.app.state.upload_dir


def _safe_script_path(upload_dir: Path, filename: str) -> Path:
    """Resolve *filename* inside *upload_dir*, rejecting traversal attempts."""
    safe = Path(filename).name
    if not safe or safe != filename or ".." in filename:
        raise HTTPException(status_code=422, detail="Invalid filename")
    path = upload_dir / safe
    if path.suffix != ".py":
        raise HTTPException(status_code=422, detail="Only .py files are allowed")
    return path


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", summary="List uploaded scripts", response_model=list[FileInfo])
def list_files(request: Request) -> list[FileInfo]:
    directory = _upload_dir(request)
    return [FileInfo(name=f.name, size=f.stat().st_size) for f in sorted(directory.iterdir()) if f.is_file() and f.suffix == ".py"]


@router.post("/upload", summary="Upload a Python script")
async def upload_file(file: UploadFile, request: Request) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")

    directory = _upload_dir(request)
    target = _safe_script_path(directory, file.filename)

    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_UPLOAD_BYTES} byte limit")

    target.write_bytes(contents)
    return {"status": "ok", "filename": target.name, "size": len(contents)}


@router.post("/execute", summary="Execute an uploaded script", response_model=ExecuteResponse)
def execute_file(body: ExecuteRequest, request: Request) -> ExecuteResponse:
    directory = _upload_dir(request)
    script = _safe_script_path(directory, body.filename)

    if not script.is_file():
        raise HTTPException(status_code=404, detail=f"Script '{body.filename}' not found")

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=body.timeout,
            cwd=str(directory),
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=408,
            detail=f"Script timed out after {body.timeout}s",
        ) from exc

    return ExecuteResponse(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)


@router.delete("/{filename}", summary="Delete an uploaded script")
def delete_file(filename: str, request: Request) -> dict[str, str]:
    directory = _upload_dir(request)
    script = _safe_script_path(directory, filename)

    if not script.is_file():
        raise HTTPException(status_code=404, detail=f"Script '{filename}' not found")

    script.unlink()
    return {"status": "ok", "filename": filename}
