from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class GitError(RuntimeError):
    pass


def git_binary() -> str:
    return (
        os.environ.get("GITSYNC_GIT")
        or shutil.which("git")
        or "/usr/bin/git"
    )


def run_git(
    repo_path: str,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:

    env = os.environ.copy()

    # Never let an unattended job wait forever for username/password input.
    env["GIT_TERMINAL_PROMPT"] = "0"

    # Rebases should never unexpectedly open an editor.
    env["GIT_EDITOR"] = "true"
    env["GIT_SEQUENCE_EDITOR"] = "true"

    result = subprocess.run(
        [git_binary(), *args],
        cwd=repo_path,
        text=True,
        capture_output=True,
        env=env,
    )

    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()

        raise GitError(
            f"git {' '.join(args)} failed: {detail}"
        )

    return result


def validate_job_config(
    repo_path: str,
    branch: str,
) -> None:

    repo = Path(repo_path).expanduser().resolve()

    if not repo.exists():
        raise ValueError(
            f"Repository path does not exist: {repo}"
        )

    result = run_git(
        str(repo),
        "rev-parse",
        "--is-inside-work-tree",
        check=False,
    )

    if result.returncode != 0:
        raise ValueError(
            f"Not a Git repository: {repo}"
        )

    branch_result = run_git(
        str(repo),
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{branch}",
        check=False,
    )

    if branch_result.returncode != 0:
        raise ValueError(
            f"Local branch does not exist: {branch}"
        )


def parse_commits(raw: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []

    for line in raw.splitlines():
        if not line.strip():
            continue

        parts = line.split("\x1f", 2)

        if len(parts) != 3:
            continue

        full_hash, short_hash, subject = parts

        commits.append(
            {
                "hash": full_hash,
                "short_hash": short_hash,
                "subject": subject,
            }
        )

    return commits


def sync_repo(
    repo_path: str,
    branch: str,
    base_branch: str,
) -> dict[str, Any]:

    repo = str(Path(repo_path).expanduser().resolve())

    result: dict[str, Any] = {
        "status": "FAILED",
        "before_head": None,
        "after_head": None,
        "incoming_commits": [],
        "message": None,
        "error": None,
    }

    try:
        validate_job_config(repo, branch)

        current_branch = run_git(
            repo,
            "branch",
            "--show-current",
        ).stdout.strip()

        if current_branch != branch:
            result["status"] = "SKIPPED_WRONG_BRANCH"
            result["message"] = (
                f"Configured branch '{branch}' is not checked out. "
                f"Current branch is '{current_branch or 'DETACHED_HEAD'}'."
            )
            return result

        dirty = run_git(
            repo,
            "status",
            "--porcelain",
        ).stdout.strip()

        if dirty:
            result["status"] = "SKIPPED_DIRTY_WORKTREE"
            result["message"] = (
                "Working tree contains uncommitted changes. "
                "GitSync did not modify the repository."
            )
            return result

        before_head = run_git(
            repo,
            "rev-parse",
            "HEAD",
        ).stdout.strip()

        result["before_head"] = before_head

        fetch = run_git(
            repo,
            "fetch",
            "--prune",
            "origin",
            base_branch,
            check=False,
        )

        if fetch.returncode != 0:
            detail = fetch.stderr.strip() or fetch.stdout.strip()

            result["status"] = "FAILED"
            result["error"] = detail
            result["message"] = (
                f"Could not fetch origin/{base_branch}."
            )
            return result

        incoming_raw = run_git(
            repo,
            "log",
            "--format=%H%x1f%h%x1f%s",
            "HEAD..FETCH_HEAD",
        ).stdout

        incoming_commits = parse_commits(incoming_raw)

        result["incoming_commits"] = incoming_commits

        if not incoming_commits:
            result["status"] = "NO_CHANGES"
            result["after_head"] = before_head
            result["message"] = (
                f"{branch} already contains the latest "
                f"origin/{base_branch} changes."
            )
            return result

        rebase = run_git(
            repo,
            "rebase",
            "FETCH_HEAD",
            check=False,
        )

        if rebase.returncode != 0:
            detail = (
                rebase.stderr.strip()
                or rebase.stdout.strip()
                or "Rebase failed."
            )

            # Restore the repository to its pre-rebase state.
            run_git(
                repo,
                "rebase",
                "--abort",
                check=False,
            )

            result["status"] = (
                "REBASE_CONFLICT"
                if "CONFLICT" in detail.upper()
                else "FAILED"
            )

            result["error"] = detail
            result["message"] = (
                "Rebase could not be completed. "
                "The rebase was aborted automatically."
            )

            return result

        after_head = run_git(
            repo,
            "rev-parse",
            "HEAD",
        ).stdout.strip()

        result["after_head"] = after_head
        result["status"] = "SUCCESS"
        result["message"] = (
            f"Rebased {branch} onto origin/{base_branch}. "
            f"{len(incoming_commits)} incoming commit(s) integrated."
        )

        return result

    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
        result["message"] = "Unexpected GitSync failure."

        return result
