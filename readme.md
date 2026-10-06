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
```

If there are uncommitted changes, GitSync safely skips the repository.

GitSync does not automatically stash changes or switch branches.

---

## Run a Sync Manually

From the dashboard, click:

```text
Run now
```

GitSync performs:

```text
Check repository
        ↓
Check configured branch is checked out
        ↓
Check working tree is clean
        ↓
git fetch origin <base-branch>
        ↓
Find incoming commits
        ↓
git rebase FETCH_HEAD
        ↓
Save run result
```

---

## Sync Results

### SUCCESS

New commits were found on the base branch and your local story branch was successfully rebased.

Example:

```text
Synced
41 incoming commits
```

---

### NO_CHANGES

Your story branch already contains the latest base branch changes.

Example:

```text
Up to date
0 incoming commits
```

This is a successful result.

---

### SKIPPED_DIRTY_WORKTREE

The repository contains uncommitted changes.

GitSync does not modify it.

Check:

```bash
git status --short
```

---

### SKIPPED_WRONG_BRANCH

The configured story branch is not currently checked out.

Check:

```bash
git branch --show-current
```

GitSync intentionally does not switch branches automatically.

---

### REBASE_CONFLICT

A Git conflict occurred while rebasing.

GitSync automatically executes:

```bash
git rebase --abort
```

and restores the repository to its pre-rebase state.

Resolve the conflict manually before trying again.

---

### FAILED

The Git operation failed for another reason.

Common causes include:

- Incorrect base branch
- Network failure
- Git authentication failure
- Repository unavailable

The full Git error is recorded in GitSync's run history.

---

## Important: What Happens After a Rebase?

GitSync updates your **local story branch**.

It intentionally does not push anything to GitHub.

Because a rebase rewrites commit hashes, Git may show:

```text
Your branch and 'origin/your-branch' have diverged
```

This is normal after rebasing a branch that already exists remotely.

For example, before the rebase:

```text
origin/master
      \
       A -- B -- C       <- remote story branch
```

After GitSync:

```text
origin/master -- new master commits
                              \
                               A' -- B' -- C'  <- local story branch
```

`A'`, `B'`, and `C'` contain the same story changes, but their Git commit hashes have changed because they were rebased onto newer base-branch history.

After verifying the result, update the remote story branch with:

```bash
git push --force-with-lease origin <your-story-branch>
```

For example:

```bash
git push --force-with-lease \
  origin \
  feature/my-story
```

Use:

```text
--force-with-lease
```

rather than:

```text
--force
```

because `--force-with-lease` refuses to overwrite unexpected remote changes made by someone else.

GitSync never performs this push automatically.

---

## Automatic Weekday Sync

Once a job is active, GitSync runs it automatically:

```text
Monday-Friday at 10:30 AM
```

The Mac must be powered on.

If the Mac is asleep around the scheduled time, macOS `launchd` can run the calendar job after the Mac wakes.

If the Mac is powered off, no local process can execute.

---

## Stop a Sync Job

When the story is finished, click:

```text
Stop sync
```

The job remains visible in GitSync and its history is preserved, but scheduled runs ignore it.

To enable it again, click:

```text
Resume
```

---

## Test the Scheduler Manually

You do not need to wait until 10:30 AM.

Trigger the scheduled runner manually:

```bash
launchctl kickstart -k \
  gui/$(id -u)/com.local.gitsync.runner
```

Check the output:

```bash
tail -30 ~/.gitsync/logs/runner.out.log
```

Check errors:

```bash
tail -30 ~/.gitsync/logs/runner.err.log
```

A successful run with no new commits looks similar to:

```text
GitSync: 1 active job(s)

[1] /Users/you/orders-service (feature/my-story)

Status: NO_CHANGES
feature/my-story already contains the latest origin/main changes.
```

---

## GitSync Data

GitSync stores its configuration and run history in:

```text
~/.gitsync/gitsync.db
```

Logs are stored under:

```text
~/.gitsync/logs/
```

---

## Uninstall

Remove the GitSync LaunchAgents:

```bash
./launchd/uninstall.sh
```

This stops GitSync but preserves its database and run history.

To remove all GitSync local data as well:

```bash
rm -rf ~/.gitsync
```