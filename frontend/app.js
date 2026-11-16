const API_BASE_URL = window.BUILDING_COMPLIANCE_CONFIG?.apiBaseUrl || (window.location.protocol + "//" + window.location.hostname + ":8000");
const proposalForm = document.getElementById("proposal-form");
const resultsSection = document.getElementById("results-section");
const resultsContent = document.getElementById("results-content");
const submitButton = document.getElementById("submit-button");
const submitLabel = submitButton.querySelector(".button-label");

function showMessage(message, type = "info", shouldScroll = false) {
  resultsSection.hidden = false;
  resultsContent.replaceChildren();
  const box = document.createElement("div");
  box.className = `result-message ${type}`;
  box.setAttribute("role", type === "error" ? "alert" : "status");
  box.textContent = message;
  resultsContent.appendChild(box);
  if (shouldScroll) resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function addResultRow(container, label, value) {
  const row = document.createElement("p");
  const heading = document.createElement("strong");
  heading.textContent = `${label}: `;
  row.append(heading, document.createTextNode(value === undefined || value === null || value === "" ? "Not provided" : String(value)));
  container.appendChild(row);
}

function addHeading(container, text) {
  const heading = document.createElement("h3");
  heading.textContent = text;
  container.appendChild(heading);
}

function getStatusPresentation(status) {
  const statusMap = {
    pending: { label: "Queued", className: "pending" },
    pending_rules_check: { label: "Awaiting regulatory checks", className: "pending" },
    running: { label: "Checking regulatory rules", className: "pending" },
    rules_retrieved: { label: "Rules retrieved — review required", className: "complete" },
    needs_review: { label: "Needs review", className: "review" },
    completed: { label: "Workflow completed — review required", className: "complete" },
    failed: { label: "Workflow failed", className: "review" },
    error: { label: "Workflow error", className: "review" }
  };
  return statusMap[status] || { label: status || "Unknown", className: "unknown" };
}

function displayFindings(container, findings) {
  addHeading(container, "Findings");
  if (!Array.isArray(findings) || findings.length === 0) {
    const message = document.createElement("p");
    message.textContent = "No findings were returned by the workflow. This does not establish compliance.";
    container.appendChild(message);
    return;
  }
  const list = document.createElement("div");
  list.className = "finding-list";
  findings.forEach((finding) => {
    const item = document.createElement("article");
    item.className = "result-clause finding-card";
    if (typeof finding === "string") {
      item.textContent = finding;
      list.appendChild(item);
      return;
    }
    const label = finding.provision || finding.rule || "Finding";
    addHeading(item, label.replaceAll("_", " "));
    const status = finding.status || finding.outcome || finding.evidence_status || "UNRESOLVED";
    const badge = document.createElement("span");
    badge.className = `finding-status finding-${String(status).toLowerCase().replaceAll("_", "-")}`;
    badge.textContent = status;
    item.appendChild(badge);
    if (finding.rule) addResultRow(item, "Rule", finding.rule);
    if (finding.source) addResultRow(item, "Source", finding.source);
    if (finding.page !== undefined && finding.page !== null) addResultRow(item, "PDF page", finding.page);
    if (finding.inputs) addResultRow(item, "Submitted inputs", JSON.stringify(finding.inputs));
    if (finding.threshold !== undefined) addResultRow(item, "Regulatory threshold", finding.threshold);
    if (finding.comparison) addResultRow(item, "Comparison", finding.comparison);
    if (finding.justification) addResultRow(item, "Why", finding.justification);
    if (finding.semantic_verification_reason) addResultRow(item, "Semantic verification", finding.semantic_verification_reason);
    if (finding.finding) addResultRow(item, "Evidence result", finding.finding);
    if (finding.evidence_excerpt) addResultRow(item, "Evidence excerpt", finding.evidence_excerpt);
    list.appendChild(item);
  });
  container.appendChild(list);
}

function displayClauses(container, clauses) {
  addHeading(container, "Retrieved regulatory clauses");
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
    title.textContent = `CLAUSE ${String(index + 1).padStart(2, "0")}`;
    article.appendChild(title);
    const source = clause.source || clause.filename || "Unknown source";
    const page = clause.page ?? clause.page_number;
    addResultRow(article, "Source", source);
    if (page !== undefined && page !== null) addResultRow(article, "PDF page", page);
    if (clause.distance !== undefined) addResultRow(article, "Retrieval distance", clause.distance);
    const text = document.createElement("p");
    text.textContent = clause.text || clause.content || clause.clause || "No clause text supplied.";
    article.appendChild(text);
    container.appendChild(article);
  });
}

function displayCitations(container, citations) {
  addHeading(container, "Sources & citations");
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
    label.textContent = page !== undefined && page !== null ? `${source}, PDF page ${page}` : source;
    item.appendChild(label);
    const excerptText = citation.text || citation.excerpt;
    if (excerptText) {
      const excerpt = document.createElement("p");
      excerpt.textContent = excerptText;
      item.appendChild(excerpt);
    }
    list.appendChild(item);
  });
  container.appendChild(list);
}

function displayVerification(container, verification, trace, llmUsage) {
  if (verification) {
    addHeading(container, "Evidence verification");
    addResultRow(container, "Citations resolve to retrieved text", verification.citations_resolved_to_retrieved_text);
    if (verification.numeric_rules_compared !== undefined) addResultRow(container, "Numeric rule comparisons", verification.numeric_rules_compared);
    if (verification.numeric_findings_unresolved !== undefined) addResultRow(container, "Numeric checks unresolved", verification.numeric_findings_unresolved);
    if (verification.prompt_version) addResultRow(container, "Prompt version", verification.prompt_version);
    if (verification.semantic_support_checked) addResultRow(container, "Groundedness / context relevance / faithfulness / hallucination", `${verification.groundedness ?? "n/a"} / ${verification.context_relevance ?? "n/a"} / ${verification.faithfulness ?? "n/a"} / ${verification.hallucination_rate ?? "n/a"}`);
    addResultRow(container, "Semantic support checked", verification.semantic_support_checked ? "Yes" : "No — human review required");
    addResultRow(container, "Currentness checked", verification.currentness_checked ? "Yes" : "No — human review required");
  }
  const verifierUsage = llmUsage?.semantic_verifier;
  if (verifierUsage) {
    addHeading(container, "Model usage and cost");
    addResultRow(container, "Verifier status", verifierUsage.status);
    if (verifierUsage.prompt_version) addResultRow(container, "Prompt version", verifierUsage.prompt_version);
    addResultRow(container, "Token usage source", verifierUsage.usage_source || "unavailable");
    addResultRow(container, "Prompt / completion tokens", `${verifierUsage.prompt_tokens ?? "n/a"} / ${verifierUsage.completion_tokens ?? "n/a"}`);
    addResultRow(container, "Cost estimate source", verifierUsage.cost_source || "unavailable");
    addResultRow(container, "Estimated cost (USD)", verifierUsage.cost_estimate_usd ?? "unavailable");
  }
  if (Array.isArray(trace) && trace.length) {
    addHeading(container, "Workflow run trace");
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

function displayResults(data, proposal) {
  resultsSection.hidden = false;
  resultsContent.replaceChildren();
  addHeading(resultsContent, "Compliance workflow status");
  const status = getStatusPresentation(data.status);
  const statusBadge = document.createElement("span");
  statusBadge.className = `result-status ${status.className}`;
  statusBadge.textContent = status.label;
  statusBadge.title = `API status: ${data.status || "unknown"}`;
  resultsContent.appendChild(statusBadge);
  if (data.run_id) addResultRow(resultsContent, "Run ID", data.run_id);
  const details = data.building_details || proposal;
  if (details) {
    addHeading(resultsContent, "Submitted building details");
    addResultRow(resultsContent, "Building use", details.building_use);
    addResultRow(resultsContent, "Plot area (m²)", details.plot_area);
    addResultRow(resultsContent, "Road width (m)", details.road_width);
    addResultRow(resultsContent, "Proposed height (m)", details.proposed_height);
    addResultRow(resultsContent, "Site width (m)", details.site_width);
    addResultRow(resultsContent, "Site depth (m)", details.site_depth);
    addResultRow(resultsContent, "Zone", details.zone);
    addResultRow(resultsContent, "Historical development area", details.development_area);
    addResultRow(resultsContent, "Proposed coverage (%)", details.proposed_coverage_percent);
    addResultRow(resultsContent, "Proposed FAR", details.proposed_far);
    addResultRow(resultsContent, "Proposed setbacks left/right/front/rear (m)", [
      details.proposed_left_setback,
      details.proposed_right_setback,
      details.proposed_front_setback,
      details.proposed_rear_setback
    ].join(" / "));
  }
  if (data.recommendation) addResultRow(resultsContent, "Recommendation", data.recommendation);
  displayFindings(resultsContent, data.findings);
  displayClauses(resultsContent, data.clauses);
  displayCitations(resultsContent, data.citations);
  displayVerification(resultsContent, data.verification, data.tool_trace, data.llm_usage);
  const disclaimer = document.createElement("p");
  disclaimer.className = "result-disclaimer";
  disclaimer.textContent = "These results show retrieved regulatory text, not a verified legal compliance decision. The applicable jurisdiction, current regulations, amendments and site-specific requirements must be independently verified by a qualified professional or the relevant authority.";
  resultsContent.appendChild(disclaimer);
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

proposalForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!proposalForm.reportValidity()) return;
  const formData = new FormData(proposalForm);
  const optionalNumber = (name) => {
    const value = formData.get(name);
    return value === null || String(value).trim() === "" ? null : Number(value);
  };
  const proposal = {
    building_use: formData.get("building_use"),
    plot_area: Number(formData.get("plot_area")),
    road_width: Number(formData.get("road_width")),
    proposed_height: Number(formData.get("proposed_height")),
    zone: String(formData.get("zone") || "").trim(),
    site_width: formData.get("site_width") ? Number(formData.get("site_width")) : null,
    site_depth: formData.get("site_depth") ? Number(formData.get("site_depth")) : null,
    proposed_coverage_percent: optionalNumber("proposed_coverage_percent"),
    proposed_far: optionalNumber("proposed_far"),
    development_area: formData.get("development_area") || null,
    proposed_left_setback: optionalNumber("proposed_left_setback"),
    proposed_right_setback: optionalNumber("proposed_right_setback"),
    proposed_front_setback: optionalNumber("proposed_front_setback"),
    proposed_rear_setback: optionalNumber("proposed_rear_setback")
  };
  const requiredNumbers = [proposal.plot_area, proposal.road_width, proposal.proposed_height];
  if (requiredNumbers.some((value) => !Number.isFinite(value) || value <= 0) || !proposal.zone ||
      (proposal.site_width !== null && (!Number.isFinite(proposal.site_width) || proposal.site_width <= 0)) ||
      (proposal.site_depth !== null && (!Number.isFinite(proposal.site_depth) || proposal.site_depth <= 0)) ||
      [proposal.proposed_left_setback, proposal.proposed_right_setback, proposal.proposed_front_setback, proposal.proposed_rear_setback]
        .some((value) => value !== null && (!Number.isFinite(value) || value < 0))) {
    showMessage("Enter valid positive measurements and a zone before starting the review.", "error", true);
    return;
  }
  if (proposal.site_width !== null && proposal.site_depth !== null && proposal.plot_area > proposal.site_width * proposal.site_depth) {
    showMessage("The plot area cannot be larger than the site width multiplied by site depth.", "error", true);
    return;
  }
  submitButton.disabled = true;
  submitLabel.textContent = "Starting your review…";
  try {
    showMessage("Submitting your proposal to the evidence review workflow…", "info", true);
    const response = await fetch(`${API_BASE_URL}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(proposal)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Submission failed (${response.status}): ${errorText}`);
    }
    let data = await response.json();
    if (!data.run_id) throw new Error("The API response did not include a run ID.");
    displayResults(data, proposal);
    const terminalStatuses = new Set(["completed", "rules_retrieved", "needs_review", "failed", "error"]);
    for (let attempt = 0; attempt < 60; attempt++) {
      if (terminalStatuses.has(data.status)) break;
      showMessage(`Your review is in progress — current status: ${data.status || "processing"}. This page will update automatically.`);
      await sleep(1000);
      const statusResponse = await fetch(`${API_BASE_URL}/runs/${encodeURIComponent(data.run_id)}`, {
        method: "GET",
        headers: { "Accept": "application/json" }
      });
      if (!statusResponse.ok) {
        const errorText = await statusResponse.text();
        throw new Error(`Status check failed (${statusResponse.status}): ${errorText}`);
      }
      data = await statusResponse.json();
      displayResults(data, proposal);
    }
    if (!terminalStatuses.has(data.status)) {
      const message = document.createElement("p");
      message.textContent = "The workflow has not finished within 60 seconds. Save the run ID and check the backend for the latest status.";
      resultsContent.appendChild(message);
    } else if (data.status === "failed" || data.status === "error") {
      showMessage("The compliance workflow could not finish. Check the backend logs for details.", "error");
    }
  } catch (error) {
    console.error("Compliance workflow request failed:", error);
    showMessage(`Could not complete the workflow: ${error.message}. Check that the API is reachable at the configured runtime address.`, "error", true);
  } finally {
    submitButton.disabled = false;
    submitLabel.textContent = "Run compliance pre-check";
  }
});
