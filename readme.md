# GitSync

GitSync is a lightweight macOS utility that automatically keeps your local feature/story branches up to date with their base branch.

It includes a local dashboard where you can:

- Add a local Git repository and story branch
- Choose the base branch (`main`, `master`, etc.)
- Run a sync immediately
- Automatically sync Monday-Friday at 10:30 AM
- Stop or resume individual sync jobs
- View previous runs
- See which commits came from the base branch
- See whether a run succeeded, had no changes, was skipped, or failed

GitSync uses `git fetch` + `git rebase` underneath.

It does **not** automatically:

- switch branches
- modify a repository with uncommitted changes
- push to GitHub
- force-push branches
- resolve rebase conflicts

If a rebase encounters a conflict, GitSync automatically runs:

```bash
git rebase --abort
```

so the repository is not left in a partially rebased state.

---

## Requirements

GitSync currently supports macOS.

You need:

- macOS
- Python 3.10+
- Git
- A local clone of the repository you want to sync
- Working Git authentication for that repository

Verify:

```bash
python3 --version
git --version
```

---

## Installation

### 1. Clone GitSync

```bash
git clone <GITSYNC_REPOSITORY_URL>
cd gitsync
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
```

### 3. Install dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

### 4. Run the GitSync smoke test

```bash
.venv/bin/python smoke_test.py
```

Expected output:

```text
GitSync smoke test

SUCCESS                      -> SUCCESS
NO_CHANGES                   -> NO_CHANGES
SKIPPED_DIRTY_WORKTREE       -> SKIPPED_DIRTY_WORKTREE
SKIPPED_WRONG_BRANCH         -> SKIPPED_WRONG_BRANCH

PASS: GitSync core behaved correctly.
```

The smoke test uses temporary repositories and does not modify your actual Git repositories.

---

## Install GitSync on macOS

Make the installer executable:

```bash
chmod +x launchd/install.sh
```

Install the GitSync background services:

```bash
./launchd/install.sh
```

GitSync installs two macOS LaunchAgents:

```text
com.local.gitsync.web
com.local.gitsync.runner
```

### Web service

Keeps the GitSync dashboard available locally.

### Scheduled runner

Runs enabled GitSync jobs:

```text
Monday-Friday
10:30 AM
```

---

## Open GitSync

After installation:

```bash
open http://127.0.0.1:8765
```

Or open the following URL in your browser:

```text
http://127.0.0.1:8765
```

GitSync listens only on `127.0.0.1`, so the dashboard is accessible only from your Mac.

---

## Add a Sync Job

Click:

```text
New Sync
```

Enter the **local path** of the repository.

Example:

```text
/Users/your-user/Documents/GitHub/orders-service
```

Do not enter the GitHub URL.

GitSync operates on your local Git checkout.

Enter your feature/story branch:

```text
feature/my-story
```

Then enter the branch you want to stay synchronized with:

```text
main
```

or:

```text
master
```

You can determine the default branch of a repository with:

```bash
git remote show origin | grep "HEAD branch"
```

For example:

```text
HEAD branch: master
```

---

## Before Running a Sync

The configured story branch must already be checked out.

Check:

```bash
git branch --show-current
```

The repository must also have a clean working tree:

```bash
git status --short
