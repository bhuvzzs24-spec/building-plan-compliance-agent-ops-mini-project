
import json
from pathlib import Path


EVALUATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "sloka_evaluation.json"
)


def load_evaluation():
    with EVALUATION_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def test_evaluation_has_twenty_unique_scenarios():
    data = load_evaluation()
    scenarios = data["scenarios"]

    assert len(scenarios) >= 20
    assert len({item["id"] for item in scenarios}) == len(scenarios)


def test_evaluation_has_two_prompt_variants():
    data = load_evaluation()

    assert len(data["prompt_variants"]) == 2
    assert {item["id"] for item in data["prompt_variants"]} == {"A", "B"}


def test_evaluation_defines_required_metrics():
    data = load_evaluation()
    metrics = data["metrics"]

    assert "retrieval_hit_rate_at_5" in metrics
    assert "citation_completeness" in metrics
    assert "evidence_support_rate" in metrics
    assert "abstention_accuracy" in metrics
    assert "scenario_pass_rate" in metrics


def test_evaluation_protocol_expects_forty_runs():
    data = load_evaluation()
    protocol = data["evaluation_protocol"]

    assert protocol["total_cases"] == 20
    assert protocol["total_prompt_runs"] == 40
    assert protocol["run_each_scenario_with"] == ["A", "B"]
