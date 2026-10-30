
const API_BASE_URL = window.BUILDING_COMPLIANCE_CONFIG?.apiBaseUrl || (window.location.protocol + "//" + window.location.hostname + ":8000");

const proposalForm = document.getElementById("proposal-form");
const resultsSection = document.getElementById("results-section");
const resultsContent = document.getElementById("results-content");

function showMessage(message, type = "info") {
    resultsSection.hidden = false;
    resultsContent.replaceChildren();

    const messageBox = document.createElement("div");
    messageBox.className = `result-message ${type}`;
    messageBox.setAttribute("role", type === "error" ? "alert" : "status");
    messageBox.textContent = message;

    resultsContent.appendChild(messageBox);
}

function addResultRow(container, label, value) {
    const row = document.createElement("p");
    const heading = document.createElement("strong");

    heading.textContent = `${label}: `;
    row.appendChild(heading);
    row.appendChild(
        document.createTextNode(
            value === undefined || value === null || value === ""
                ? "Not provided"
                : String(value)
        )
    );

    container.appendChild(row);
}

function addHeading(container, text) {
    const heading = document.createElement("h3");
    heading.textContent = text;
    container.appendChild(heading);
}

function getStatusPresentation(status) {
    const statusMap = {
        pending: {
            label: "Queued",
            className: "pending"
        },
        pending_rules_check: {
            label: "Awaiting regulatory checks",
            className: "pending"
        },
        running: {
            label: "Checking regulatory rules",
            className: "pending"
        },
        rules_retrieved: {
            label: "Rules retrieved — review required",
            className: "complete"
        },
        needs_review: {
            label: "Needs review",
            className: "review"
        },
        completed: {
            label: "Workflow completed — review required",
            className: "complete"
        },
        failed: {
            label: "Workflow failed",
            className: "review"
        },
        error: {
            label: "Workflow error",
            className: "review"
        }
    };

    return statusMap[status] || {
        label: status || "Unknown",
        className: "unknown"
    };
}

function displayFindings(container, findings) {
    addHeading(container, "Findings");

    if (!Array.isArray(findings) || findings.length === 0) {
        const message = document.createElement("p");
        message.textContent =
            "No findings were returned by the workflow. This does not establish compliance.";
        container.appendChild(message);
        return;
    }

    const list = document.createElement("ul");

    findings.forEach((finding) => {
        const item = document.createElement("li");

        if (typeof finding === "string") {
            item.textContent = finding;
        } else {
            item.textContent =
                finding.message ||
                finding.description ||
                JSON.stringify(finding);
        }

        list.appendChild(item);
    });

    container.appendChild(list);
}

function displayClauses(container, clauses) {
    addHeading(container, "Retrieved Regulatory Clauses");

    if (!Array.isArray(clauses) || clauses.length === 0) {
        const message = document.createElement("p");
        message.textContent = "No regulatory clauses were returned.";
        container.appendChild(message);
        return;
    }

    clauses.forEach((clause, index) => {
        const article = document.createElement("article");
        article.className = "result-clause";

        const title = document.createElement("h4");
        title.textContent = `Clause ${index + 1}`;
        article.appendChild(title);

        const source = clause.source || clause.filename || "Unknown source";
        const page = clause.page ?? clause.page_number;

        addResultRow(article, "Source", source);

        if (page !== undefined && page !== null) {
            addResultRow(article, "PDF page", page);
        }

        if (clause.distance !== undefined) {
            addResultRow(article, "Retrieval distance", clause.distance);
        }

        const text = document.createElement("p");
        text.textContent =
            clause.text || clause.content || clause.clause || "No clause text supplied.";
        article.appendChild(text);

        container.appendChild(article);
    });
}

function displayCitations(container, citations) {
    addHeading(container, "Sources and Citations");

    if (!Array.isArray(citations) || citations.length === 0) {
        const message = document.createElement("p");
        message.textContent = "No citations were returned by the workflow.";
        container.appendChild(message);
        return;
    }

    const list = document.createElement("ol");

    citations.forEach((citation) => {
        const item = document.createElement("li");
        const source = citation.source || citation.filename || "Unknown source";
        const page = citation.page ?? citation.page_number;

        const label = document.createElement("strong");
        label.textContent =
            page !== undefined && page !== null
                ? `${source}, PDF page ${page}`
                : source;

        item.appendChild(label);

        if (citation.text) {
            const excerpt = document.createElement("p");
            excerpt.textContent = citation.text;
            item.appendChild(excerpt);
        }

        list.appendChild(item);
    });

    container.appendChild(list);
}

function displayResults(data, proposal) {
    resultsSection.hidden = false;
    resultsContent.replaceChildren();

    addHeading(resultsContent, "Compliance Workflow Status");

    const status = getStatusPresentation(data.status);
    const statusBadge = document.createElement("span");

    statusBadge.className = `result-status ${status.className}`;
    statusBadge.textContent = status.label;
    statusBadge.title = `API status: ${data.status || "unknown"}`;

    resultsContent.appendChild(statusBadge);

    if (data.run_id) {
        addResultRow(resultsContent, "Run ID", data.run_id);
    }

    const details = data.building_details || proposal;

    if (details) {
        addHeading(resultsContent, "Submitted Building Details");
        addResultRow(resultsContent, "Building use", details.building_use);
        addResultRow(resultsContent, "Plot area (m²)", details.plot_area);
        addResultRow(resultsContent, "Road width (m)", details.road_width);
        addResultRow(
            resultsContent,
            "Proposed height (m)",
            details.proposed_height
        );
        addResultRow(resultsContent, "Zone", details.zone);
    }

    if (data.recommendation) {
        addResultRow(resultsContent, "Recommendation", data.recommendation);
    }
    displayFindings(resultsContent, data.findings);
    displayClauses(resultsContent, data.clauses);
    displayCitations(resultsContent, data.citations);
    displayVerification(resultsContent, data.verification, data.tool_trace);

    const disclaimer = document.createElement("p");
    disclaimer.className = "result-disclaimer";
    disclaimer.textContent =
        "These results show retrieved regulatory text, not a verified legal compliance decision. " +
        "The applicable jurisdiction, current regulations, amendments, and site-specific requirements " +
        "must be independently verified by a qualified professional or the relevant authority.";

    resultsContent.appendChild(disclaimer);
}

function displayVerification(container, verification, trace) {
    if (verification) {
        addHeading(container, "Evidence Verification");
        addResultRow(container, "Citations resolve to retrieved text", verification.citations_resolved_to_retrieved_text);
        addResultRow(container, "Semantic support checked", verification.semantic_support_checked ? "Yes" : "No — human review required");
        addResultRow(container, "Currentness checked", verification.currentness_checked ? "Yes" : "No — human review required");
    }
    if (Array.isArray(trace) && trace.length) {
        addHeading(container, "Run Trace");
        const list = document.createElement("ol");
        trace.forEach((step) => {
            const item = document.createElement("li");
            item.textContent = (step.step || "step") + " / " + (step.tool || "workflow") +
                (step.topic ? " / " + step.topic : "") +
                (step.duration_seconds !== undefined ? " / " + step.duration_seconds + "s" : "") +
                (step.error_type ? " / error: " + step.error_type : "");
            list.appendChild(item);
        });
        container.appendChild(list);
    }
}
function sleep(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

proposalForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!proposalForm.reportValidity()) {
        return;
    }

    const formData = new FormData(proposalForm);

    const proposal = {
        building_use: formData.get("building_use"),
        plot_area: Number(formData.get("plot_area")),
        road_width: Number(formData.get("road_width")),
        proposed_height: Number(formData.get("proposed_height")),
        zone: String(formData.get("zone") || "").trim(),
        site_width: formData.get("site_width") ? Number(formData.get("site_width")) : null,
        site_depth: formData.get("site_depth") ? Number(formData.get("site_depth")) : null,
        proposed_coverage_percent: formData.get("proposed_coverage_percent") ? Number(formData.get("proposed_coverage_percent")) : null,
        proposed_far: formData.get("proposed_far") ? Number(formData.get("proposed_far")) : null
    };

    if (
        !Number.isFinite(proposal.plot_area) ||
        !Number.isFinite(proposal.road_width) ||
        !Number.isFinite(proposal.proposed_height) ||
        proposal.plot_area <= 0 ||
        proposal.road_width <= 0 ||
        proposal.proposed_height <= 0 ||
        !proposal.zone ||
        (proposal.site_width !== null && !Number.isFinite(proposal.site_width)) ||
        (proposal.site_depth !== null && !Number.isFinite(proposal.site_depth))
    ) {
        showMessage("Enter valid positive measurements and a zone.", "error");
        return;
    }

    const submitButton = proposalForm.querySelector('button[type="submit"]');

    submitButton.disabled = true;
    submitButton.textContent = "Checking proposal...";

    try {
        showMessage("Submitting proposal to the compliance workflow...", "info");

        const response = await fetch(`${API_BASE_URL}/runs`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(proposal)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Submission failed (${response.status}): ${errorText}`);
        }

        let data = await response.json();

        if (!data.run_id) {
            throw new Error("The API response did not include a run ID.");
        }

        displayResults(data, proposal);

        const terminalStatuses = new Set([
            "completed",
            "rules_retrieved",
            "needs_review",
            "failed",
            "error"
        ]);

        for (let attempt = 0; attempt < 60; attempt++) {
            if (terminalStatuses.has(data.status)) {
                break;
            }

            showMessage(
                `Workflow status: ${data.status || "processing"}. Waiting for results...`,
                "info"
            );

            await sleep(1000);

            const statusResponse = await fetch(
                `${API_BASE_URL}/runs/${encodeURIComponent(data.run_id)}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            if (!statusResponse.ok) {
                const errorText = await statusResponse.text();
                throw new Error(
                    `Status check failed (${statusResponse.status}): ${errorText}`
                );
            }

            data = await statusResponse.json();
            displayResults(data, proposal);
        }

        if (!terminalStatuses.has(data.status)) {
            const message = document.createElement("p");
            message.textContent =
                "The workflow has not finished within 60 seconds. " +
                "Submit again later or check the run ID with the backend.";
            resultsContent.appendChild(message);
        } else if (
            data.status === "failed" ||
            data.status === "error"
        ) {
            showMessage(
                "The compliance workflow failed. Check the backend terminal for details.",
                "error"
            );
        }
    } catch (error) {
        console.error("Compliance workflow request failed:", error);

        showMessage(
            `Could not complete the workflow: ${error.message}. ` +
            "Check that the API is reachable at the configured runtime address.",
            "error"
        );
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Check Building Proposal";
    }
});

