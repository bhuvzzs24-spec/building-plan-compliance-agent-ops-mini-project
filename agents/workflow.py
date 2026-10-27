from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import RetryPolicy

from agents.rag.retriever import retrieve_clauses


class ComplianceState(TypedDict, total=False):
    building_details: dict[str, Any]
    findings: list[str]
    status: str
    clauses: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    retry_count: int


def validate_building_details(
    state: ComplianceState,
) -> dict[str, Any]:
    details = state.get("building_details", {})
    findings = list(state.get("findings", []))

    required_fields = (
        "building_use",
        "plot_area",
        "road_width",
        "proposed_height",
        "zone",
    )

    for field in required_fields:
        value = details.get(field)
        if value is None or (
            isinstance(value, str) and not value.strip()
        ):
            findings.append(f"Missing required field: {field}")

    for field in ("plot_area", "road_width", "proposed_height"):
        value = details.get(field)
        if value is not None:
            try:
                if float(value) <= 0:
                    findings.append(
                        f"{field} must be greater than zero."
                    )
            except (TypeError, ValueError):
                findings.append(f"{field} must be a number.")

    findings = list(dict.fromkeys(findings))
    return {
        "findings": findings,
        "status": "needs_review" if findings else "pending_rules_check",
        "retry_count": 0,
    }


def retrieval_agent(
    state: ComplianceState,
) -> dict[str, Any]:
    details = state.get("building_details", {})
    question = (
        "Building bye-laws relevant to this proposal: "
        + ", ".join(f"{key}: {value}" for key, value in details.items())
    )

    try:
        clauses = retrieve_clauses(question, top_k=5)
    except Exception:
        findings = list(state.get("findings", []))
        findings.append(
            "Building-code retrieval failed; manual review required."
        )
        return {
            "clauses": [],
            "citations": [],
            "findings": list(dict.fromkeys(findings)),
            "status": "needs_review",
        }

    return {"clauses": clauses}


def citation_verification_agent(
    state: ComplianceState,
) -> dict[str, Any]:
    findings = list(state.get("findings", []))
    citations = []

    for clause in state.get("clauses", []):
        text = str(clause.get("text", "")).strip()
        source = clause.get("source")
        page = clause.get("page")

        if not text or not isinstance(source, str) or not source.strip():
            continue
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            continue

        citations.append({
            "source": source,
            "page": page,
            "text": text,
        })

    if not citations:
        findings.append(
            "No traceable building-code evidence was found; "
            "manual review required."
        )

    findings = list(dict.fromkeys(findings))
    return {
        "citations": citations,
        "findings": findings,
        "status": (
            "needs_review"
            if findings or not citations
            else "rules_retrieved"
        ),
    }


def build_compliance_workflow():
    graph = StateGraph(ComplianceState)

    graph.add_node(
        "validate_building_details",
        validate_building_details,
    )
    graph.add_node(
        "retrieval_agent",
        retrieval_agent,
        retry_policy=RetryPolicy(max_attempts=3),
    )
    graph.add_node(
        "citation_verification_agent",
        citation_verification_agent,
    )

    graph.set_entry_point("validate_building_details")
    graph.add_edge("validate_building_details", "retrieval_agent")
    graph.add_edge("retrieval_agent", "citation_verification_agent")
    graph.add_edge("citation_verification_agent", END)

    return graph.compile()


compliance_workflow = build_compliance_workflow()
