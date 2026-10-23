
from typing import TypedDict, Any

from langgraph.graph import StateGraph, END
from agents.rag.retriever import retrieve_clauses


class ComplianceState(TypedDict):
    building_details: dict[str, Any]
    findings: list[str]
    status: str
    clauses: list[dict[str, Any]]
    citations: list[dict[str, Any]]


def validate_building_details(state: ComplianceState) -> dict[str, Any]:
    details = state.get("building_details", {})
    findings = list(state.get("findings", []))
    required = [
        "building_use", "plot_area", "road_width",
        "proposed_height", "zone",
    ]

    for field in required:
        if field not in details:
            findings.append(f"Missing required field: {field}")

    for field in ["plot_area", "road_width", "proposed_height"]:
        if field in details:
            try:
                if float(details[field]) <= 0:
                    findings.append(f"{field} must be greater than zero.")
            except (TypeError, ValueError):
                findings.append(f"{field} must be a number.")

    return {
        "findings": findings,
        "status": "needs_review" if findings else "pending_rules_check",
    }


def retrieve_building_rules(state: ComplianceState) -> dict[str, Any]:
    details = state.get("building_details", {})
    question = (
        "Building bye-laws relevant to this proposal: "
        + ", ".join(f"{key}: {value}" for key, value in details.items())
    )

    clauses = retrieve_clauses(question, top_k=5)
    return {"clauses": clauses}


def verify_citations(state: ComplianceState) -> dict[str, Any]:
    clauses = state.get("clauses", [])
    findings = list(state.get("findings", []))
    citations = []

    for clause in clauses:
        source = clause.get("source")
        page = clause.get("page")
        text = clause.get("text", "").strip()

        if source and page is not None and text:
            citations.append({
                "source": source,
                "page": page,
                "text": text,
            })

    if not citations:
        findings.append(
            "No verifiable supporting clauses found; manual review required."
        )
        status = "needs_review"
    elif findings:
        status = "needs_review"
    else:
        status = "rules_retrieved"

    return {
        "citations": citations,
        "findings": findings,
        "status": status,
    }


def build_compliance_workflow():
    graph = StateGraph(ComplianceState)
    graph.add_node("validate_building_details", validate_building_details)
    graph.add_node("retrieve_building_rules", retrieve_building_rules)
    graph.add_node("verify_citations", verify_citations)

    graph.set_entry_point("validate_building_details")
    graph.add_edge("validate_building_details", "retrieve_building_rules")
    graph.add_edge("retrieve_building_rules", "verify_citations")
    graph.add_edge("verify_citations", END)

    return graph.compile()


compliance_workflow = build_compliance_workflow()
