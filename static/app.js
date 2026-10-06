const jobsContainer =
    document.getElementById("jobs");

const emptyState =
    document.getElementById("emptyState");

const modal =
    document.getElementById("jobModal");

const backdrop =
    document.getElementById("modalBackdrop");

const drawer =
    document.getElementById("historyDrawer");

const toast =
    document.getElementById("toast");


const deleteModal =
    document.getElementById("deleteModal");

const confirmDeleteButton =
    document.getElementById(
        "confirmDeleteButton"
    );

let pendingDeleteJobId = null;
let jobsCache = [];



function escapeHtml(value = "") {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function repoName(path) {
    const parts =
        path.replace(/\/+$/, "").split("/");

    return parts[parts.length - 1];
}


function formatDate(value) {
    if (!value) {
        return "Never run";
    }

    const date = new Date(value);

    return new Intl.DateTimeFormat(
        undefined,
        {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
        }
    ).format(date);
}


function statusTone(status) {
    if (
        status === "SUCCESS" ||
        status === "NO_CHANGES"
    ) {
        return "good";
    }

    if (
        status === "SKIPPED_DIRTY_WORKTREE" ||
        status === "SKIPPED_WRONG_BRANCH"
    ) {
        return "warn";
    }

    if (
        status === "FAILED" ||
        status === "REBASE_CONFLICT"
    ) {
        return "bad";
    }

    return "";
}


function statusLabel(status) {
    const labels = {
        SUCCESS: "Synced",
        NO_CHANGES: "Up to date",
        SKIPPED_DIRTY_WORKTREE:
            "Local changes detected",
        SKIPPED_WRONG_BRANCH:
            "Different branch checked out",
        REBASE_CONFLICT:
            "Rebase conflict",
        FAILED:
            "Failed",
    };

    return labels[status] || "Not run yet";
}


function showToast(message) {
    toast.textContent = message;
    toast.classList.add("visible");

    clearTimeout(window.toastTimer);

    window.toastTimer = setTimeout(
        () => toast.classList.remove("visible"),
        2600
    );
}


function openModal() {
    modal.classList.add("visible");
    backdrop.classList.add("visible");

    setTimeout(
        () =>
            document
                .getElementById("repoPath")
                .focus(),
        150
    );
}


function closeModal() {
    modal.classList.remove("visible");

    if (!drawer.classList.contains("visible")) {
        backdrop.classList.remove("visible");
    }
}


function closeHistory() {
    drawer.classList.remove("visible");

    if (!modal.classList.contains("visible")) {
        backdrop.classList.remove("visible");
    }
}


window.openModal = openModal;
window.closeModal = closeModal;
window.closeHistory = closeHistory;


async function api(
    url,
    options = {}
) {
    const response = await fetch(
        url,
        {
            headers: {
                "Content-Type":
                    "application/json",
                ...(options.headers || {}),
            },
            ...options,
        }
    );

    let payload = {};

    try {
        payload = await response.json();
    } catch (_) {}

    if (!response.ok) {
        throw new Error(
            payload.detail ||
            `Request failed: ${response.status}`
        );
    }

    return payload;
}


function jobCard(job) {
    const enabled = Boolean(job.enabled);

    const tone =
        statusTone(job.last_status);

    const incoming =
        job.last_incoming_count || 0;

    const message =
        job.last_status
            ? (
                incoming > 0
                    ? `${incoming} incoming commit${
                        incoming === 1 ? "" : "s"
                    }`
                    : job.last_message ||
                      statusLabel(job.last_status)
            )
            : "Waiting for first sync";

    return `
        <article
            class="job-card"
            id="job-${job.id}"
        >

            <div class="job-top">

                <div>
                    <div class="repo-name">
                        ${escapeHtml(
                            repoName(job.repo_path)
                        )}
                    </div>

                    <div
                        class="repo-path"
                        title="${escapeHtml(job.repo_path)}"
                    >
                        ${escapeHtml(job.repo_path)}
                    </div>
                </div>

                <div
                    class="status-pill ${
                        enabled ? "active" : ""
                    }"
                >
                    ${enabled ? "ACTIVE" : "STOPPED"}
                </div>

            </div>

            <div class="branch-row">

                <span>
                    ${escapeHtml(job.branch)}
                </span>

                <span class="branch-arrow">
                    →
                </span>

                <span class="base-branch">
                    origin/${escapeHtml(
                        job.base_branch
                    )}
                </span>

            </div>

            <div class="last-result">

                <div class="result-title">

                    <span
                        class="result-dot ${tone}"
                    ></span>

                    ${
                        job.last_status
                            ? statusLabel(
                                job.last_status
                              )
                            : "Ready"
                    }

                </div>

                <div class="result-meta">
                    ${escapeHtml(message)}
                    ·
                    ${formatDate(job.last_run_at)}
                </div>

            </div>

            <div class="job-actions">

                <button
                    class="action-button"
                    onclick="showHistory(
                        ${job.id},
                        '${escapeHtml(
                            repoName(job.repo_path)
                        )}'
                    )"
                >
                    History
                </button>

                <button
                    class="action-button ${
                        enabled ? "" : "danger"
                    }"
                    onclick="${
                        enabled
                            ? `stopJob(${job.id})`
                            : `resumeJob(${job.id})`
                    }"
                >
                    ${
                        enabled
                            ? "Stop sync"
                            : "Resume"
                    }
                </button>

                <button
                    class="action-button delete-action"
                    onclick="requestDelete(${job.id})"
                >
                    Delete
                </button>

                <button
                    class="action-button run"
                    ${
                        enabled
                            ? ""
                            : "disabled"
                    }
                    onclick="runJob(${job.id}, this)"
                >
                    Run now
                </button>

            </div>

        </article>
    `;
}


async function loadJobs() {
    try {
        const data =
            await api("/api/jobs");

        const jobs =
            data.jobs || [];

        jobsCache = jobs;

        jobsContainer.innerHTML =
            jobs.map(jobCard).join("");

        emptyState.classList.toggle(
            "visible",
            jobs.length === 0
        );

        const active =
            jobs.filter(
                j => Boolean(j.enabled)
            ).length;

        const clean =
            jobs.filter(
                j =>
                    j.last_status ===
                        "SUCCESS" ||
                    j.last_status ===
                        "NO_CHANGES"
            ).length;

        const attention =
            jobs.filter(
                j =>
                    j.last_status &&
                    ![
                        "SUCCESS",
                        "NO_CHANGES",
                    ].includes(
                        j.last_status
                    )
            ).length;

        document.getElementById(
            "activeCount"
        ).textContent = active;

        document.getElementById(
            "cleanCount"
        ).textContent = clean;

        document.getElementById(
            "attentionCount"
        ).textContent = attention;

    } catch (error) {
        showToast(error.message);
    }
}


async function runJob(
    jobId,
    button
) {
    const card =
        document.getElementById(
            `job-${jobId}`
        );

    try {
        button.disabled = true;
        button.textContent = "Running…";

        card.classList.add("running");

        const result =
            await api(
                `/api/jobs/${jobId}/run`,
                {
                    method: "POST",
                }
            );

        showToast(
            statusLabel(result.status)
        );

        await loadJobs();

    } catch (error) {
        showToast(error.message);

    } finally {
        card?.classList.remove("running");

        if (button) {
            button.disabled = false;
            button.textContent = "Run now";
        }
    }
}


async function stopJob(jobId) {
    try {
        await api(
            `/api/jobs/${jobId}/stop`,
            {
                method: "POST",
            }
        );

        showToast(
            "Scheduled sync stopped"
        );

        await loadJobs();

    } catch (error) {
        showToast(error.message);
    }
}


async function resumeJob(jobId) {
    try {
        await api(
            `/api/jobs/${jobId}/resume`,
            {
                method: "POST",
            }
        );

        showToast(
            "Scheduled sync resumed"
        );

        await loadJobs();

    } catch (error) {
        showToast(error.message);
    }
}


async function showHistory(
    jobId,
    name
) {
    try {
        document.getElementById(
            "drawerTitle"
        ).textContent = name;

        document.getElementById(
            "historyContent"
        ).innerHTML =
            "<p class='result-meta'>Loading…</p>";

        drawer.classList.add("visible");
        backdrop.classList.add("visible");

        const data =
            await api(
                `/api/jobs/${jobId}/runs`
            );

        const runs =
            data.runs || [];

        if (!runs.length) {
            document.getElementById(
                "historyContent"
            ).innerHTML = `
                <p class="result-meta">
                    No runs yet.
                </p>
            `;

            return;
        }

        document.getElementById(
            "historyContent"
        ).innerHTML =
            runs.map(run => {

                const tone =
                    statusTone(run.status);

                const commits =
                    (run.incoming_commits || [])
                    .map(commit => `
                        <div class="commit">
                            <span class="commit-hash">
                                ${escapeHtml(
                                    commit.short_hash
                                )}
                            </span>

                            <span class="commit-subject">
                                ${escapeHtml(
                                    commit.subject
                                )}
                            </span>
                        </div>
                    `)
                    .join("");

                return `
                    <div class="history-item ${tone}">

                        <div class="history-status">
                            ${escapeHtml(
                                statusLabel(run.status)
                            )}
                        </div>

                        <div class="history-date">
                            ${formatDate(
                                run.finished_at ||
                                run.started_at
                            )}
                            ·
                            ${escapeHtml(
                                run.trigger_type
                            )}
                        </div>

                        ${
                            run.message
                                ? `
                                    <div class="history-message">
                                        ${escapeHtml(
                                            run.message
                                        )}
                                    </div>
                                `
                                : ""
                        }

                        ${
                            commits
                                ? `
                                    <div class="commit-list">
                                        ${commits}
                                    </div>
                                `
                                : ""
                        }

                        ${
                            run.error
                                ? `
                                    <div class="error-text">
                                        ${escapeHtml(
                                            run.error
                                        )}
                                    </div>
                                `
                                : ""
                        }

                    </div>
                `;
            })
            .join("");

    } catch (error) {
        showToast(error.message);
    }
}




function requestDelete(jobId) {
    const job =
        jobsCache.find(
            item => item.id === jobId
        );

    if (!job) {
        showToast(
            "Could not find sync job"
        );
        return;
    }

    pendingDeleteJobId = jobId;

    const repository =
        repoName(job.repo_path);

    const branch =
        job.branch;

    document.getElementById(
        "deleteJobDescription"
    ).innerHTML = `
        Delete
        <strong>${escapeHtml(repository)}</strong>
        /
        <strong>${escapeHtml(branch)}</strong>?
        <br><br>
        This permanently removes the sync job
        and all of its GitSync run history.
    `;

    deleteModal.classList.add(
        "visible"
    );

    backdrop.classList.add(
        "visible"
    );
}


function cancelDelete() {
    pendingDeleteJobId = null;

    deleteModal.classList.remove(
        "visible"
    );

    if (
        !modal.classList.contains(
            "visible"
        ) &&
        !drawer.classList.contains(
            "visible"
        )
    ) {
        backdrop.classList.remove(
            "visible"
        );
    }
}


async function deleteJob() {
    if (!pendingDeleteJobId) {
        return;
    }

    const jobId =
        pendingDeleteJobId;

    try {
        confirmDeleteButton.disabled =
            true;

        confirmDeleteButton.textContent =
            "Deleting…";

        await api(
            `/api/jobs/${jobId}`,
            {
                method: "DELETE",
            }
        );

        cancelDelete();

        showToast(
            "Sync job deleted"
        );

        await loadJobs();

    } catch (error) {
        showToast(
            error.message
        );

    } finally {
        confirmDeleteButton.disabled =
            false;

        confirmDeleteButton.textContent =
            "Delete Sync";
    }
}


window.requestDelete =
    requestDelete;

window.cancelDelete =
    cancelDelete;


confirmDeleteButton.addEventListener(
    "click",
    deleteJob
);


window.runJob = runJob;
window.stopJob = stopJob;
window.resumeJob = resumeJob;
window.showHistory = showHistory;


document
    .getElementById("openAddJob")
    .addEventListener(
        "click",
        openModal
    );


document
    .getElementById("refreshJobs")
    .addEventListener(
        "click",
        loadJobs
    );


backdrop.addEventListener(
    "click",
    () => {
        closeModal();
        closeHistory();
        cancelDelete();
    }
);


document
    .getElementById("jobForm")
    .addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            const button =
                event.currentTarget
                    .querySelector(
                        "button[type='submit']"
                    );

            try {
                button.disabled = true;
                button.textContent =
                    "Adding…";

                await api(
                    "/api/jobs",
                    {
                        method: "POST",

                        body: JSON.stringify({
                            repo_path:
                                document
                                    .getElementById(
                                        "repoPath"
                                    )
                                    .value
                                    .trim(),

                            branch:
                                document
                                    .getElementById(
                                        "branch"
                                    )
                                    .value
                                    .trim(),

                            base_branch:
                                document
                                    .getElementById(
                                        "baseBranch"
                                    )
                                    .value
                                    .trim(),
                        }),
                    }
                );

                event.currentTarget.reset();

                document.getElementById(
                    "baseBranch"
                ).value = "main";

                closeModal();

                showToast(
                    "Sync job created"
                );

                await loadJobs();

            } catch (error) {
                showToast(error.message);

            } finally {
                button.disabled = false;
                button.textContent =
                    "Start Sync";
            }
        }
    );



function updateNextRunDate() {
    const element =
        document.getElementById(
            "nextRunDate"
        );

    if (!element) {
        return;
    }

    const now = new Date();

    let nextRun = new Date(now);

    nextRun.setHours(
        10,
        30,
        0,
        0
    );

    const isWeekday = date => {
        const day = date.getDay();

        return day >= 1 && day <= 5;
    };

    /*
     * If today's 10:30 window has already passed,
     * move to tomorrow.
     */
    if (
        !isWeekday(nextRun) ||
        now >= nextRun
    ) {
        nextRun.setDate(
            nextRun.getDate() + 1
        );

        nextRun.setHours(
            10,
            30,
            0,
            0
        );
    }

    /*
     * Skip Saturday and Sunday.
     */
    while (!isWeekday(nextRun)) {
        nextRun.setDate(
            nextRun.getDate() + 1
        );
    }

    const formatted =
        new Intl.DateTimeFormat(
            undefined,
            {
                weekday: "long",
                day: "numeric",
                month: "long",
            }
        ).format(nextRun);

    element.textContent =
        formatted;
}


updateNextRunDate();
loadJobs();

setInterval(
    loadJobs,
    30000
);


setInterval(
    updateNextRunDate,
    60000
);
