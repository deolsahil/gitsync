from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_DIR = Path.home() / ".gitsync"
DB_PATH = DB_DIR / "gitsync.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_path TEXT NOT NULL,
                branch TEXT NOT NULL,
                base_branch TEXT NOT NULL DEFAULT 'main',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                UNIQUE(repo_path, branch)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                before_head TEXT,
                after_head TEXT,
                incoming_count INTEGER NOT NULL DEFAULT 0,
                incoming_commits TEXT,
                message TEXT,
                error TEXT,

                FOREIGN KEY(job_id)
                    REFERENCES jobs(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_runs_job_id
                ON runs(job_id);

            CREATE INDEX IF NOT EXISTS idx_runs_started_at
                ON runs(started_at);
            """
        )


def add_job(
    repo_path: str,
    branch: str,
    base_branch: str = "main",
) -> dict[str, Any]:

    repo_path = str(Path(repo_path).expanduser().resolve())

    now = utc_now()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO jobs (
                repo_path,
                branch,
                base_branch,
                enabled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (
                repo_path,
                branch,
                base_branch,
                now,
                now,
            ),
        )

        job_id = cursor.lastrowid

    return get_job(job_id)


def get_job(job_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()

    return dict(row) if row else None


def list_jobs() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                j.*,

                (
                    SELECT status
                    FROM runs r
                    WHERE r.job_id = j.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS last_status,

                (
                    SELECT finished_at
                    FROM runs r
                    WHERE r.job_id = j.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS last_run_at,

                (
                    SELECT incoming_count
                    FROM runs r
                    WHERE r.job_id = j.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS last_incoming_count,

                (
                    SELECT message
                    FROM runs r
                    WHERE r.job_id = j.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS last_message

            FROM jobs j
            ORDER BY j.id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def set_job_enabled(
    job_id: int,
    enabled: bool,
) -> dict[str, Any] | None:

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET
                enabled = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                int(enabled),
                utc_now(),
                job_id,
            ),
        )

    return get_job(job_id)


def delete_job(job_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        )

    return cursor.rowcount > 0


def create_run(
    job_id: int,
    trigger_type: str,
) -> int:

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO runs (
                job_id,
                trigger_type,
                started_at,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                job_id,
                trigger_type,
                utc_now(),
                "RUNNING",
            ),
        )

        return cursor.lastrowid


def finish_run(
    run_id: int,
    status: str,
    *,
    before_head: str | None = None,
    after_head: str | None = None,
    incoming_commits: list[dict[str, str]] | None = None,
    message: str | None = None,
    error: str | None = None,
) -> None:

    commits = incoming_commits or []

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE runs
            SET
                finished_at = ?,
                status = ?,
                before_head = ?,
                after_head = ?,
                incoming_count = ?,
                incoming_commits = ?,
                message = ?,
                error = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                status,
                before_head,
                after_head,
                len(commits),
                json.dumps(commits),
                message,
                error,
                run_id,
            ),
        )


def list_runs(
    job_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:

    with get_connection() as conn:

        if job_id is None:
            rows = conn.execute(
                """
                SELECT *
                FROM runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        else:
            rows = conn.execute(
                """
                SELECT *
                FROM runs
                WHERE job_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    job_id,
                    limit,
                ),
            ).fetchall()

    results = []

    for row in rows:
        item = dict(row)

        raw = item.get("incoming_commits")

        try:
            item["incoming_commits"] = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            item["incoming_commits"] = []

        results.append(item)

    return results
