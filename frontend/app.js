
const API_BASE_URL = "https://building-plan-compliance-agent-ops-mini.onrender.com";

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
    row.appendChild(document.createTextNode(String(value)));

    container.appendChild(row);
}

function addHeading(container, text) {
    const heading = document.createElement("h3");
    heading.textContent = text;
    container.appendChild(heading);
}

function getStatusPresentation(status) {
    const statusMap = {
        pending_rules_check: {
            label: "Awaiting regulatory checks",
            className: "pending"
        },
        needs_review: {
            label: "Needs review",
            className: "review"
        },
        completed: {
            label: "Completed",
            className: "complete"
        }
    };

    return statusMap[status] || {
        label: status || "Unknown",
        className: "unknown"
    };
}

function displayResults(data) {
    resultsSection.hidden = false;
    resultsContent.replaceChildren();

    addHeading(resultsContent, "Compliance Check Status");

    const status = getStatusPresentation(data.status);
    const statusBadge = document.createElement("span");

    statusBadge.className = `result-status ${status.className}`;
    statusBadge.textContent = status.label;
    statusBadge.title = `API status: ${data.status || "unknown"}`;

    resultsContent.appendChild(statusBadge);

    if (data.building_details) {
        addHeading(resultsContent, "Submitted Building Details");

        const details = data.building_details;

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

    addHeading(resultsContent, "Findings");

    if (Array.isArray(data.findings) && data.findings.length > 0) {
        const findingsList = document.createElement("ul");

        data.findings.forEach((finding) => {
            const item = document.createElement("li");
            item.textContent = finding;
            findingsList.appendChild(item);
        });

        resultsContent.appendChild(findingsList);
    } else {
        const noFindings = document.createElement("p");
        noFindings.textContent = "No basic input validation findings.";
        resultsContent.appendChild(noFindings);
    }

    const disclaimer = document.createElement("p");
    disclaimer.className = "result-disclaimer";
    disclaimer.textContent =
        "This is a preliminary input-validation response, not a verified " +
        "building compliance decision. Actual regulatory checks and citations " +
        "are not yet provided by this endpoint.";

    resultsContent.appendChild(disclaimer);
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
        zone: formData.get("zone").trim()
    };

    if (
        !Number.isFinite(proposal.plot_area) ||
        !Number.isFinite(proposal.road_width) ||
        !Number.isFinite(proposal.proposed_height) ||
        proposal.plot_area <= 0 ||
        proposal.road_width <= 0 ||
        proposal.proposed_height <= 0 ||
        !proposal.zone
    ) {
        showMessage(
            "Enter valid positive measurements and a zone.",
            "error"
        );
        return;
    }

    const submitButton = proposalForm.querySelector(
        'button[type="submit"]'
    );

    submitButton.disabled = true;
    submitButton.textContent = "Checking proposal...";
    showMessage("Sending your proposal to the backend...", "info");

    try {
        const response = await fetch(`${API_BASE_URL}/check`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(proposal)
        });

        const data = await response.json();

        if (!response.ok) {
            const message =
                typeof data.detail === "string"
                    ? data.detail
                    : "The API rejected the request.";

            showMessage(
                `Request failed (${response.status}): ${message}`,
                "error"
            );
            return;
        }

        displayResults(data);
    } catch (error) {
        console.error("Proposal request failed:", error);

        showMessage(
            "Could not connect to the backend. Check that FastAPI is " +
            "running at http://127.0.0.1:8000.",
            "error"
        );
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Check Building Proposal";
    }
});
