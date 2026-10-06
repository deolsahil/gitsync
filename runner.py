from __future__ import annotations

import sys

from db import (
    create_run,
    finish_run,
    get_job,
    init_db,
    list_jobs,
)

from git_sync import sync_repo


def execute_job(
    job: dict,
    trigger_type: str,
) -> dict:

    run_id = create_run(
        job["id"],
        trigger_type,
    )

    result = sync_repo(
        repo_path=job["repo_path"],
        branch=job["branch"],
        base_branch=job["base_branch"],
    )

    finish_run(
        run_id,
        result["status"],
        before_head=result.get("before_head"),
        after_head=result.get("after_head"),
        incoming_commits=result.get("incoming_commits"),
        message=result.get("message"),
        error=result.get("error"),
    )

    result["run_id"] = run_id

    return result


def execute_job_by_id(
    job_id: int,
    trigger_type: str = "manual",
) -> dict:

    job = get_job(job_id)

    if not job:
        raise ValueError(
            f"Job {job_id} does not exist."
        )

    return execute_job(
        job,
        trigger_type,
    )


def run_scheduled_jobs() -> int:
    init_db()

    jobs = [
        job
        for job in list_jobs()
        if job["enabled"]
    ]

    print(
        f"GitSync: {len(jobs)} active job(s)"
    )

    failures = 0

    for job in jobs:
        print(
            f"\n[{job['id']}] "
            f"{job['repo_path']} "
            f"({job['branch']})"
        )

        result = execute_job(
            job,
            "scheduled",
        )

        print(
            f"Status: {result['status']}"
        )

        if result.get("message"):
            print(result["message"])

        if result.get("error"):
            print(
                f"Error: {result['error']}",
                file=sys.stderr,
            )

        if result["status"] in {
            "FAILED",
            "REBASE_CONFLICT",
        }:
            failures += 1

    return failures


if __name__ == "__main__":
    raise SystemExit(
        1 if run_scheduled_jobs() else 0
    )
