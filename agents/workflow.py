from __future__ import annotations

from hashlib import sha256
from functools import lru_cache
from pathlib import Path
import time
import os
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import RetryPolicy

from agents.rag.retriever import retrieve_clauses
from backend.app.metrics import metrics


MAX_STEPS = 3
MAX_TOOL_CALLS = 6
SEARCH_TOP_K = 4


class ComplianceState(TypedDict, total=False):
    building_details: dict[str, Any]
    planned_queries: list[tuple[str, str]]
    tool_calls: int
    verified_clauses: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    status: str
    clauses: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    obligations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    verification: dict[str, Any]
    recommendation: str
    review_reasons: list[str]
    retry_count: int


def lookup_request_fields(details: dict[str, Any], names: list[str]) -> dict[str, Any]:
    """Agent tool: read only the proposal fields named by the planner."""
    return {name: details.get(name) for name in names}


@lru_cache(maxsize=512)
def _cached_search(query: str, persist_dir: str, top_k: int, index_version: str):
    return retrieve_clauses(query, persist_dir, top_k)


def search_corpus(query: str, top_k: int = SEARCH_TOP_K) -> list[dict[str, Any]]:
    """Agent tool with process-local cache invalidated by the index manifest."""
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
    manifest = Path(os.getenv("INDEX_MANIFEST_PATH", str(Path(persist_dir).parent / "index_manifest.json")))
    try:
        index_version = str(manifest.stat().st_mtime_ns)
    except OSError:
        index_version = "manifest-missing"
    before = _cached_search.cache_info().hits
    result = _cached_search(query, persist_dir, top_k, index_version)
    after = _cached_search.cache_info().hits
    metrics.increment("retrieval_cache_hits_total" if after > before else "retrieval_cache_misses_total")
    return [dict(item) for item in result]


def lookup_clauses_by_location(
    locations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agent tool: re-resolve citations against the persisted corpus."""
    import chromadb

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection("building_bye_laws")
    resolved: list[dict[str, Any]] = []
    for location in locations:
        source = location.get("source")
        page = location.get("page")
        if not isinstance(source, str) or not isinstance(page, int):
            continue
        found = collection.get(
            where={"$and": [{"source": source}, {"page": page}]},
            include=["documents", "metadatas"],
        )
        for text, metadata in zip(found.get("documents") or [], found.get("metadatas") or []):
            if text and metadata.get("source") == source and metadata.get("page") == page:
                resolved.append({
                    "source": source,
                    "page": page,
                    "text": text,
                    "clause_id": sha256(f"{source}:{page}:{text}".encode("utf-8")).hexdigest()[:16],
                })
    return resolved


def _plan_queries(details: dict[str, Any]) -> list[tuple[str, str]]:
    use = str(details.get("building_use", "")).strip()
    area = details.get("plot_area", "unknown")
    road = details.get("road_width", "unknown")
    height = details.get("proposed_height", "unknown")
    zone = str(details.get("zone", "unknown")).strip()
    base = f"proposal use {use} plot area {area} square metres zone {zone}"
    # Target separate clauses because a single broad semantic query can miss
    # road-conditioned FAR/height provisions that sit apart from setback tables.
    queries = [
        ("setbacks", f"{base} setback table site width depth proposed height {height}"),
        ("road_width_height", f"{base} abutting road width {road} maximum height road width height limit"),
        ("far_coverage", f"{base} road width {road} floor area ratio FAR ground coverage plot coverage"),
    ]
    if use:
        queries.append(("permitted_use", f"{base} zone permitted land use zoning regulations"))
    return queries[:MAX_TOOL_CALLS - 2]


def plan_review(state: ComplianceState) -> dict[str, Any]:
    details = state.get("building_details", {})
    fields = lookup_request_fields(
        details,
        ["building_use", "plot_area", "road_width", "proposed_height", "zone", "site_width", "site_depth"],
    )
    reasons = []
    if fields.get("site_width") is None or fields.get("site_depth") is None:
        reasons.append("Site width and depth are needed to evaluate setback tables.")
    return {
        "planned_queries": _plan_queries(details),
        "tool_calls": 1,
        "tool_trace": [{
            "step": "proposal-inspection",
            "tool": "lookup_request_fields",
            "fields_read": list(fields),
            "result": "required and optional fields inspected",
        }],
        "review_reasons": reasons,
        "status": "planned",
    }


def retrieve_provisions(state: ComplianceState) -> dict[str, Any]:
    passages: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    trace = list(state.get("tool_trace", []))
    calls = int(state.get("tool_calls", 1))

    for topic, query in state.get("planned_queries", []):
        if calls >= MAX_TOOL_CALLS - 1:
            break
        calls += 1
        try:
            call_started = time.perf_counter()
            results = search_corpus(query, SEARCH_TOP_K)
            trace.append({
                "step": "provision-discovery",
                "tool": "search_corpus",
                "topic": topic,
                "query": query,
                "returned": len(results),
                "duration_seconds": round(time.perf_counter() - call_started, 6),
            })
            for item in results:
                item = dict(item)
                item["topic"] = topic
                passages.append(item)
            obligations.append({
                "provision": topic,
                "evidence_count": len(results),
                "status": "evidence-found" if results else "evidence-missing",
            })
        except Exception as exc:
            trace.append({
                "step": "provision-discovery",
                "tool": "search_corpus",
                "topic": topic,
                "error_type": type(exc).__name__,
            })
            obligations.append({
                "provision": topic,
                "evidence_count": 0,
                "status": "retrieval-failed",
            })

    # Deduplicate by source/page/text while keeping the topic associations.
    unique: dict[tuple[str, Any, str], dict[str, Any]] = {}
    for clause in passages:
        key = (
            str(clause.get("source", "")),
            clause.get("page"),
            str(clause.get("text", "")),
        )
        if key in unique:
            topics = set(unique[key].get("topics", []))
            topics.add(clause["topic"])
            unique[key]["topics"] = sorted(topics)
        else:
            clause["topics"] = [clause.pop("topic")]
            unique[key] = clause

    clauses = list(unique.values())
    locations = list({
        (item.get("source"), item.get("page"))
        for item in clauses
        if item.get("source") and isinstance(item.get("page"), int)
    })
    locations = [{"source": source, "page": page} for source, page in locations]

    verified = []
    if locations and calls < MAX_TOOL_CALLS:
        calls += 1
        try:
            verified = lookup_clauses_by_location(locations)
            trace.append({
                "step": "citation-recheck",
                "tool": "lookup_clauses_by_location",
                "requested": len(locations),
                "resolved": len(verified),
            })
        except Exception as exc:
            trace.append({
                "step": "citation-recheck",
                "tool": "lookup_clauses_by_location",
                "error_type": type(exc).__name__,
            })

    return {
        "clauses": clauses,
        "verified_clauses": verified,
        "obligations": obligations,
        "tool_trace": trace,
        "tool_calls": calls,
        "status": "evidence-retrieved",
    }


def verify_evidence_and_route(state: ComplianceState) -> dict[str, Any]:
    retrieved = state.get("clauses", [])
    resolved = state.get("verified_clauses", [])
    retrieved_keys = {
        (item.get("source"), item.get("page"), item.get("text"))
        for item in retrieved
    }
    citations = [
        item for item in resolved
        if (item.get("source"), item.get("page"), item.get("text")) in retrieved_keys
        and item.get("text")
        and isinstance(item.get("source"), str)
        and isinstance(item.get("page"), int)
        and not isinstance(item.get("page"), bool)
        and item.get("page") > 0
    ]
    reasons = list(state.get("review_reasons", []))
    missing_topics = [
        item["provision"] for item in state.get("obligations", [])
        if item["status"] != "evidence-found"
    ]
    if missing_topics:
        reasons.append("Evidence is missing or retrieval failed for: " + ", ".join(missing_topics))
    if len(citations) != len(retrieved):
        reasons.append("One or more citations could not be resolved to exact persisted text.")
    # The checked-in corpus snapshot is not confirmed as the current, complete
    # authority-issued corpus. No route may imply legal clearance from it.
    reasons.append("Current regulatory version and property-specific applicability require authority/professional confirmation.")
    findings = [
        {
            "provision": item["provision"],
            "evidence_status": item["status"],
            "finding": "Potentially relevant clauses retrieved; substantive compliance is not determined.",
            "citations": [
                {
                    "source": citation["source"],
                    "page": citation["page"],
                    "clause_id": citation["clause_id"],
                }
                for citation in citations
                if item["provision"] in next(
                    (clause.get("topics", []) for clause in retrieved
                     if clause.get("source") == citation["source"]
                     and clause.get("page") == citation["page"]
                     and clause.get("text") == citation["text"]),
                    [],
                )
            ],
        }
        for item in state.get("obligations", [])
    ]
    verification = {
        "verified": bool(citations) and len(citations) == len(retrieved),
        "retrieved_passages": len(retrieved),
        "citations_resolved_to_retrieved_text": len(citations),
        "semantic_support_checked": False,
        "currentness_checked": False,
    }
    return {
        "citations": citations,
        "findings": findings,
        "verification": verification,
        "review_reasons": list(dict.fromkeys(reasons)),
        "recommendation": "specialist-review",
        "status": "completed",
    }


def build_compliance_workflow():
    graph = StateGraph(ComplianceState)
    graph.add_node("retrieval_planner_agent", plan_review)
    graph.add_node(
        "provision_discovery_agent",
        retrieve_provisions,
        retry_policy=RetryPolicy(max_attempts=2, initial_interval=0.25, backoff_factor=2.0),
    )
    graph.add_node("evidence_verification_agent", verify_evidence_and_route)
    graph.set_entry_point("retrieval_planner_agent")
    graph.add_edge("retrieval_planner_agent", "provision_discovery_agent")
    graph.add_edge("provision_discovery_agent", "evidence_verification_agent")
    graph.add_edge("evidence_verification_agent", END)
    return graph.compile()


compliance_workflow = build_compliance_workflow()






