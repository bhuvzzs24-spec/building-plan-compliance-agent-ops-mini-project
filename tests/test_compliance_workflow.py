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
