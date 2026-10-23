
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the project root so Python can import the agents package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.rag.retriever import retrieve_clauses


DATASET_PATH = ROOT / "evaluation" / "sloka_evaluation.json"
RESULTS_PATH = ROOT / "evaluation" / "sloka_evaluation_results.json"


def load_dataset():
    """Load and validate the evaluation scenarios."""
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if isinstance(dataset, list):
        scenarios = dataset
    elif isinstance(dataset, dict):
        scenarios = (
            dataset.get("scenarios")
            or dataset.get("cases")
            or dataset.get("evaluation_cases")
        )
    else:
        scenarios = None

    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(
            "Could not find a non-empty scenario list in "
            "evaluation/sloka_evaluation.json. Check its JSON structure."
        )

    return scenarios


def get_question(scenario):
    """Support common question-field names in the dataset."""
    for key in ("question", "query", "prompt", "input"):
        value = scenario.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raise ValueError(
        "A scenario is missing a question/query/prompt/input field: "
        + str(scenario)
    )


def get_scenario_id(scenario, index):
    """Use the scenario's existing ID when available."""
    return scenario.get(
        "id",
        scenario.get("scenario_id", f"scenario_{index:02d}")
    )


def main():
    scenarios = load_dataset()
    results = []

    total = len(scenarios)

    for index, scenario in enumerate(scenarios, start=1):
        if not isinstance(scenario, dict):
            print(f"Skipping invalid scenario {index}: not a JSON object.")
            continue

        scenario_id = get_scenario_id(scenario, index)

        try:
            question = get_question(scenario)
        except ValueError as error:
            print(f"Skipping scenario {scenario_id}: {error}")
            continue

        print(f"[{index}/{total}] Evaluating {scenario_id}...")

        try:
            retrieved = retrieve_clauses(question, top_k=5)

            if retrieved is None:
                retrieved = []

            if not isinstance(retrieved, list):
                retrieved = list(retrieved)

            expected = (
                scenario.get("expected_sources")
                or scenario.get("expected_source")
                or []
            )
            if isinstance(expected, str):
                expected = [expected]

            passages = []
            for item in retrieved:
                if isinstance(item, dict):
                    passages.append(item)
                elif hasattr(item, "page_content"):
                    metadata = getattr(item, "metadata", {}) or {}
                    passages.append({
                        "text": item.page_content,
                        "source": metadata.get("source"),
                        "page": metadata.get("page"),
                        "metadata": metadata,
                    })
                else:
                    passages.append({"text": str(item)})

            def passage_text(passage):
                return str(
                    passage.get("text")
                    or passage.get("content")
                    or passage.get("page_content")
                    or ""
                )

            def passage_source(passage):
                metadata = passage.get("metadata", {}) or {}
                return str(
                    passage.get("source")
                    or metadata.get("source")
                    or ""
                )

            retrieved_sources = [
                passage_source(passage)
                for passage in passages
                if passage_source(passage)
            ]

            # This is a source-name hit proxy, not a semantic relevance score.
            expected_names = [
                str(source).lower()
                for source in expected
            ]
            source_hit = (
                any(
                    expected_name in retrieved_source.lower()
                    for expected_name in expected_names
                    for retrieved_source in retrieved_sources
                )
                if expected_names
                else None
            )

            citation_complete_count = sum(
                bool(passage_text(passage).strip())
                and bool(passage_source(passage).strip())
                and (
                    passage.get("page") is not None
                    or (passage.get("metadata", {}) or {}).get("page") is not None
                )
                for passage in passages
            )

            results.append({
                "scenario_id": scenario_id,
                "question": question,
                "prompt_variants_executed": [],
                "prompt_variants_note": (
                    "This script evaluates retrieval only. It does not call an "
                    "LLM or execute prompt variants."
                ),
                "retrieved_count": len(passages),
                "retrieval_hit_at_5_source_proxy": source_hit,
                "citation_completeness": (
                    citation_complete_count / len(passages)
                    if passages else 0.0
                ),
                "evidence_support_rate": None,
                "abstention_accuracy": None,
                "scenario_pass_rate": None,
                "manual_review_required": True,
                "retrieved_passages": [
                    {
                        "text": passage_text(passage),
                        "source": passage_source(passage) or None,
                        "page": (
                            passage.get("page")
                            if passage.get("page") is not None
                            else (passage.get("metadata", {}) or {}).get("page")
                        ),
                    }
                    for passage in passages
                ],
                "error": None,
            })

        except Exception as error:
            results.append({
                "scenario_id": scenario_id,
                "question": question,
                "retrieved_count": 0,
                "retrieval_hit_at_5_source_proxy": None,
                "citation_completeness": 0.0,
                "evidence_support_rate": None,
                "abstention_accuracy": None,
                "scenario_pass_rate": None,
                "manual_review_required": True,
                "retrieved_passages": [],
                "error": f"{type(error).__name__}: {error}",
            })
            print(f"  ERROR: {type(error).__name__}: {error}")

    report = {
        "evaluation_name": "Sloka Building Plan Compliance RAG Evaluation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "total_scenarios_in_dataset": total,
        "scenarios_processed": len(results),
        "scenarios_with_errors": sum(
            result.get("error") is not None for result in results
        ),
        "evaluation_scope": (
            "Retrieval and citation-metadata checks only. This run does not "
            "execute LLM prompt variants and does not establish semantic "
            "evidence support, abstention accuracy, or overall compliance accuracy."
        ),
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print()
    print("Evaluation finished.")
    print(f"Scenarios processed: {len(results)}/{total}")
    print(f"Scenarios with errors: {report['scenarios_with_errors']}")
    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
