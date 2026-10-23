from typing import TypedDict, Any

from langgraph.graph import StateGraph, END
from agents.rag.retriever import retrieve_clauses


class ComplianceState(TypedDict):
    building_details: dict[str, Any]
    findings: list[str]
    status: str
    clauses: list[dict[str, Any]]


def validate_building_details(state: ComplianceState) -> dict[str, Any]:
    details = state.get('building_details', {})
    findings = list(state.get('findings', []))
    required_fields = ['building_use', 'plot_area', 'road_width', 'proposed_height', 'zone']

    for field in required_fields:
        if field not in details:
            findings.append(f'Missing required field: {field}')

    for field in ['plot_area', 'road_width', 'proposed_height']:
        if field in details:
            try:
                if float(details[field]) <= 0:
                    findings.append(f'{field} must be greater than zero.')
            except (TypeError, ValueError):
                findings.append(f'{field} must be a number.')

    return {'findings': findings, 'status': 'needs_review' if findings else 'pending_rules_check'}


def retrieve_building_rules(state: ComplianceState) -> dict[str, Any]:
    details = state.get('building_details', {})
    question = 'Building bye-laws for ' + ', '.join(f'{key}: {value}' for key, value in details.items())
    clauses = retrieve_clauses(question, top_k=5)
    findings = list(state.get('findings', []))
    for clause in clauses:
        findings.append(f"Bye-law reference: {clause['text']} (Source: {clause['source']}, page: {clause['page']})")
    return {'clauses': clauses, 'findings': findings, 'status': 'rules_retrieved' if clauses else 'needs_review'}


def build_compliance_workflow():
    graph = StateGraph(ComplianceState)
    graph.add_node('validate_building_details', validate_building_details)
    graph.add_node('retrieve_building_rules', retrieve_building_rules)
    graph.set_entry_point('validate_building_details')
    graph.add_edge('validate_building_details', 'retrieve_building_rules')
    graph.add_edge('retrieve_building_rules', END)
    return graph.compile()


compliance_workflow = build_compliance_workflow()
