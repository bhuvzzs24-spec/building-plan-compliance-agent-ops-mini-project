from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from agents.rag.retriever import retrieve_clauses


class ComplianceState(TypedDict):
    building_details: dict[str, Any]
    findings: list[str]
    status: str
    clauses: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    retry_count: int


def validate_building_details(state):
    details = state.get("building_details", {})
    findings = list(state.get("findings", []))

    for field in ("building_use", "plot_area", "road_width",
                  "proposed_height", "zone"):
        if field not in details or details[field] in ("", None):
            findings.append(f"Missing required field: {field}")

    for field in ("plot_area", "road_width", "proposed_height"):
        if field in details:
            try:
                if float(details[field]) <= 0:
                    findings.append(f"{field} must be greater than zero.")
            except (TypeError, ValueError):
                findings.append(f"{field} must be a number.")

    return {
        "findings": list(dict.fromkeys(findings)),
        "status": "needs_review" if findings else "pending_rules_check",
        "retry_count": 0,
    }


# Agent 1: retrieve relevant evidence.
def retrieval_agent(state):
    details = state.get("building_details", {})
    question = (
        "Building bye-laws relevant to this proposal: "
        + ", ".join(f"{k}: {v}" for k, v in details.items())
    )
    clauses = retrieve_clauses(question, top_k=5)
    return {"clauses": clauses}


# Agent 2: check citation metadata and evidence relevance.
# This is a heuristic check, not an authoritative legal or semantic verifier.
def citation_verification_agent(state):
    clauses = state.get("clauses", [])
    findings = list(state.get("findings", []))
    citations = []

    for clause in clauses:
        text = str(clause.get("text", "")).strip()
        source = clause.get("source")
        page = clause.get("page")

        if not text or not source or page is None:
            continue

        citations.append({
            "source": source,
            "page": page,
            "text": text,
        })

    if not citations:
        findings.append(
            "Evidence could not be verified; manual review required."
        )
        return {
            "citations": [],
            "findings": list(dict.fromkeys(findings)),
            "status": "needs_review",
        }

    if findings:
        status = "needs_review"
    else:
        status = "rules_retrieved"

    return {
        "citations": citations,
        "findings": list(dict.fromkeys(findings)),
        "status": status,
    }


def build_compliance_workflow():
    graph = StateGraph(ComplianceState)
    graph.add_node("validate_building_details", validate_building_details)
    graph.add_node("retrieval_agent", retrieval_agent)
    graph.add_node("citation_verification_agent",
                   citation_verification_agent)

    graph.set_entry_point("validate_building_details")
    graph.add_edge("validate_building_details", "retrieval_agent")
    graph.add_edge("retrieval_agent", "citation_verification_agent")
    graph.add_edge("citation_verification_agent", END)
    return graph.compile()


compliance_workflow = build_compliance_workflow()