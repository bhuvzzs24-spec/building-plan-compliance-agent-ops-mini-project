from agents import workflow


def sample_clause(source, page, text):
    return {
        "source": source,
        "page": page,
        "text": text,
        "distance": 0.1,
    }


def test_planner_creates_separate_narrow_road_queries():
    details = {
        "building_use": "residential",
        "plot_area": 200,
        "road_width": 6,
        "proposed_height": 9,
        "zone": "A",
        "site_width": 10,
        "site_depth": 20,
    }
    planned = workflow.plan_review({"building_details": details})
    queries = dict(planned["planned_queries"])

    assert "setback" in queries["setbacks"].lower()
    assert "road width" in queries["road_width_height"].lower()
    assert "floor area ratio" in queries["far_coverage"].lower()
    assert planned["tool_calls"] == 1


def test_workflow_retrieves_distinct_provisions_and_escalates(monkeypatch):
    details = {
        "building_use": "residential",
        "plot_area": 200,
        "road_width": 6,
        "proposed_height": 9,
        "zone": "A",
        "site_width": 10,
        "site_depth": 20,
    }
    by_page = {
        22: "Table 4: residential setbacks for buildings up to 9.5 m high.",
        24: "Table 6: coverage and FAR depend on plot area and road width.",
        27: "Road width modifies the maximum building height.",
        30: "Residential land use and permitted activities.",
    }

    def fake_search(query, top_k):
        query = query.lower()
        if "setback" in query:
            return [sample_clause("official.pdf", 22, by_page[22])]
        if "floor area ratio" in query or "ground coverage" in query:
            return [sample_clause("official.pdf", 24, by_page[24])]
        if "maximum height" in query:
            return [sample_clause("official.pdf", 27, by_page[27])]
        return [sample_clause("official.pdf", 30, by_page[30])]

    def fake_lookup(locations):
        return [
            {
                "source": "official.pdf",
                "page": location["page"],
                "text": by_page[location["page"]],
                "clause_id": f"clause-{location['page']}",
            }
            for location in locations
        ]

    monkeypatch.setattr(workflow, "search_corpus", fake_search)
    monkeypatch.setattr(workflow, "lookup_clauses_by_location", fake_lookup)
    result = workflow.compliance_workflow.invoke({
        "building_details": details,
        "findings": [],
        "clauses": [],
        "citations": [],
    })

    topics = {obligation["provision"] for obligation in result["obligations"]}
    assert {"setbacks", "road_width_height", "far_coverage"} <= topics
    assert {22, 24, 27} <= {citation["page"] for citation in result["citations"]}
    assert result["tool_calls"] <= workflow.MAX_TOOL_CALLS
    assert result["recommendation"] == "specialist-review"
    assert result["verification"]["verified"] is True
    assert result["verification"]["semantic_support_checked"] is False
    assert any("current regulatory version" in reason.lower() for reason in result["review_reasons"])


def test_missing_site_dimensions_force_review():
    state = workflow.plan_review({
        "building_details": {
            "building_use": "residential",
            "plot_area": 200,
            "road_width": 6,
            "proposed_height": 9,
            "zone": "A",
        }
    })
    assert any("Site width and depth" in reason for reason in state["review_reasons"])


def test_adaptive_retrieval_searches_for_missing_reference_tables(monkeypatch):
    details = {
        "building_use": "residential", "plot_area": 200, "road_width": 6,
        "proposed_height": 9, "zone": "Residential", "development_area": "A",
        "site_width": 10, "site_depth": 20,
    }
    searched = []

    def fake_search(query, top_k):
        searched.append(query)
        if "table 4" in query.lower():
            return [sample_clause("historic.pdf", 22, "TABLE 4 residential setback cells")]
        if "table 6" in query.lower():
            return [sample_clause("historic.pdf", 24, "TABLE 6 FAR coverage road area")]
        return [sample_clause("historic.pdf", 28, "unrelated historical passage")]

    def fake_lookup(locations):
        return [
            sample_clause(location["source"], location["page"], f"verified page {location['page']}")
            for location in locations
        ]

    monkeypatch.setattr(workflow, "search_corpus", fake_search)
    monkeypatch.setattr(workflow, "lookup_clauses_by_location", fake_lookup)
    planned = workflow.plan_review({"building_details": details})
    result = workflow.retrieve_provisions({**planned, "building_details": details})

    assert result["adaptive_searches"] == 2
    assert any("Table 4" in query for query in searched)
    assert any("Table 6" in query for query in searched)
    assert {22, 24} <= {item["page"] for item in result["clauses"]}
    assert result["tool_calls"] <= workflow.MAX_TOOL_CALLS
    assert sum(step.get("adaptive", False) for step in result["tool_trace"]) == 2


def test_historical_numeric_comparisons_use_source_table_cells():
    from hashlib import sha256
    from pathlib import Path
    from pypdf import PdfReader
    from agents.compliance import evaluate_historical_rules
    from agents.workflow import verify_evidence_and_route

    source = Path(__file__).resolve().parents[1] / "data" / "bye_laws" / "Bangalore-Building-Byelaws.pdf"
    reader = PdfReader(str(source))
    pages = []
    for page_number in (22, 24):
        text = reader.pages[page_number - 1].extract_text()
        pages.append({
            "source": source.name,
            "page": page_number,
            "text": text,
            "clause_id": sha256(f"{source.name}:{page_number}:{text}".encode()).hexdigest()[:16],
            "topics": ["setbacks" if page_number == 22 else "far_coverage"],
        })

    proposal = {
        "building_use": "residential", "plot_area": 200, "road_width": 6,
        "proposed_height": 9, "zone": "Residential (R1)", "development_area": "A",
        "site_width": 10, "site_depth": 20,
        "proposed_left_setback": 1.5, "proposed_right_setback": 1.5,
        "proposed_front_setback": 4, "proposed_rear_setback": 3,
        "proposed_coverage_percent": 60, "proposed_far": 0.7,
    }
    findings = evaluate_historical_rules(proposal, pages)
    by_name = {item["provision"]: item for item in findings}

    assert by_name["setbacks.front"]["threshold"] == ">= 4 m"
    assert by_name["setbacks.rear"]["threshold"] == ">= 3 m"
    assert by_name["far_coverage.coverage"]["threshold"] == "<= 65%"
    assert by_name["far_coverage.far"]["threshold"] == "<= 0.75"
    assert all(item["status"] == "SATISFIED" for item in findings)
    assert all(item["page"] == 22 for item in findings[:4])
    assert all(item["page"] == 24 for item in findings[4:])

    violation_proposal = {
        **proposal,
        "proposed_left_setback": 1.0,
        "proposed_coverage_percent": 70,
        "proposed_far": 0.9,
    }
    route = verify_evidence_and_route({
        "building_details": violation_proposal,
        "clauses": pages,
        "verified_clauses": pages,
        "obligations": [
            {"provision": "setbacks", "status": "evidence-found"},
            {"provision": "far_coverage", "status": "evidence-found"},
        ],
        "tool_trace": [],
        "tool_calls": 8,
    })
    assert any(item["status"] == "VIOLATED" for item in route["numerical_findings"])
    assert route["recommendation"] == "revise-and-recheck"
    assert any("current regulatory version" in reason.lower() for reason in route["review_reasons"])
