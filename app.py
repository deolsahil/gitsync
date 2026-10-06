from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from db import (
    add_job,
    delete_job,
    get_job,
    init_db,
    list_jobs,
    list_runs,
    set_job_enabled,
)

from git_sync import validate_job_config
from runner import execute_job_by_id


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="GitSync",
    docs_url=None,
    redoc_url=None,
)

init_db()

app.mount(
    "/static",
    StaticFiles(
        directory=BASE_DIR / "static"
    ),
    name="static",
)


class CreateJobRequest(BaseModel):
    repo_path: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    base_branch: str = Field(
        default="main",
        min_length=1,
    )


@app.get("/")
def home():
    return FileResponse(
        BASE_DIR / "static" / "index.html"
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "gitsync",
    }


@app.get("/api/jobs")
def jobs():
    return {
        "jobs": list_jobs()
    }


@app.post("/api/jobs")
def create_job(payload: CreateJobRequest):
    try:
        validate_job_config(
            payload.repo_path,
            payload.branch,
        )

        return add_job(
            payload.repo_path,
            payload.branch,
            payload.base_branch,
        )

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=(
                "This repository/branch "
                "already has a GitSync job."
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.post("/api/jobs/{job_id}/run")
def run_job(job_id: int):
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return execute_job_by_id(
        job_id,
        trigger_type="manual",
    )


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: int):
    job = set_job_enabled(
        job_id,
        False,
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return job


@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: int):
    job = set_job_enabled(
        job_id,
        True,
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return job


@app.delete("/api/jobs/{job_id}")
def remove_job(job_id: int):
    if not delete_job(job_id):
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return {
        "deleted": True
    }


@app.get("/api/jobs/{job_id}/runs")
def job_runs(
    job_id: int,
    limit: int = 25,
):
    if not get_job(job_id):
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return {
        "runs": list_runs(
            job_id=job_id,
            limit=min(limit, 100),
        )
    }
