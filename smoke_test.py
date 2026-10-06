from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from git_sync import sync_repo


def run(
    cwd: Path,
    *args: str,
) -> str:

    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr or result.stdout
        )

    return result.stdout.strip()


def assert_status(
    result: dict,
    expected: str,
) -> None:

    actual = result["status"]

    print(
        f"{expected:<28} -> {actual}"
    )

    if actual != expected:
        raise AssertionError(
            f"Expected {expected}, "
            f"got {actual}: {result}"
        )


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)

    origin = root / "origin.git"
    repo = root / "service"
    upstream = root / "upstream"

    run(
        root,
        "init",
        "--bare",
        str(origin),
    )

    run(
        root,
        "clone",
        str(origin),
        str(repo),
    )

    run(
        repo,
        "config",
        "user.email",
        "gitsync@test.local",
    )

    run(
        repo,
        "config",
        "user.name",
        "GitSync Test",
    )

    run(
        repo,
        "checkout",
        "-b",
        "main",
    )

    (repo / "README.md").write_text(
        "initial\n"
    )

    run(repo, "add", "README.md")

    run(
        repo,
        "commit",
        "-m",
        "initial commit",
    )

    run(
        repo,
        "push",
        "-u",
        "origin",
        "main",
    )

    run(
        origin,
        "symbolic-ref",
        "HEAD",
        "refs/heads/main",
    )

    run(
        repo,
        "checkout",
        "-b",
        "ACIP-TEST",
    )

    (repo / "story.txt").write_text(
        "story work\n"
    )

    run(repo, "add", "story.txt")

    run(
        repo,
        "commit",
        "-m",
        "story commit",
    )

    run(
        root,
        "clone",
        str(origin),
        str(upstream),
    )

    run(
        upstream,
        "config",
        "user.email",
        "upstream@test.local",
    )

    run(
        upstream,
        "config",
        "user.name",
        "Upstream Test",
    )

    (upstream / "main-change.txt").write_text(
        "new main work\n"
    )

    run(
        upstream,
        "add",
        "main-change.txt",
    )

    run(
        upstream,
        "commit",
        "-m",
        "new main commit",
    )

    run(
        upstream,
        "push",
        "origin",
        "main",
    )

    print("\nGitSync smoke test\n")

    result = sync_repo(
        str(repo),
        "ACIP-TEST",
        "main",
    )

    assert_status(
        result,
        "SUCCESS",
    )

    result = sync_repo(
        str(repo),
        "ACIP-TEST",
        "main",
    )

    assert_status(
        result,
        "NO_CHANGES",
    )

    (repo / "dirty.txt").write_text(
        "not committed\n"
    )

    result = sync_repo(
        str(repo),
        "ACIP-TEST",
        "main",
    )

    assert_status(
        result,
        "SKIPPED_DIRTY_WORKTREE",
    )

    (repo / "dirty.txt").unlink()

    run(
        repo,
        "checkout",
        "main",
    )

    result = sync_repo(
        str(repo),
        "ACIP-TEST",
        "main",
    )

    assert_status(
        result,
        "SKIPPED_WRONG_BRANCH",
    )

print("\nPASS: GitSync core behaved correctly.")
