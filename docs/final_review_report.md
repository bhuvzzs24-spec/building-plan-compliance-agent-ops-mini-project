# Building Plan Compliance Pre-Check Service
## Final Project Review and Testing Report

### 1. Project Overview

The Building Plan Compliance Pre-Check Service is a prototype that retrieves relevant building bye-law passages for a proposed building and presents the retrieved evidence with source and page citations. It is intended to assist preliminary review, not replace an authorized building-plan review or legal determination.

The project combines a FastAPI backend, a browser-based frontend, a LangGraph workflow, and a ChromaDB-backed retrieval pipeline.

### 2. Implemented Architecture

The current workflow follows these steps:

1. **Input validation:** Checks required building details and verifies that plot area, road width, and proposed height are positive numeric values.
2. **Rule retrieval:** Searches the indexed building bye-law corpus for potentially relevant passages.
3. **Citation verification:** Checks that retrieved passages contain text, source metadata, and a valid page number.
4. **Result presentation:** Returns findings, retrieved clauses, citations, and a review status through the API and frontend.
5. **Failure handling:** Adds a manual-review finding when retrieval fails or traceable evidence is unavailable.

The retrieval node has a configured maximum of three attempts through LangGraph's retry policy.

### 3. Testing and Verification

The final automated test run completed successfully:

| Check | Result |
|---|---|
| Automated test suite | 23 passed |
| Test execution time | 7.84 seconds |
| Test failures | 0 |
| Frontend/backend integration | Manually confirmed by the developer |
| Retrieval and citation display | Manually confirmed by the developer |
| GitHub push | Previously confirmed |
| Git working tree | Previously confirmed clean |

The test suite includes API, evaluation-configuration, and RAG indexing/retrieval/citation tests.

These results establish that the existing tests pass. They do not establish complete regulatory accuracy, production readiness, or compliance with every assignment requirement.

### 4. Evaluation Status

The evaluation dataset contains 20 scenarios and defines two prompt variants:

- **Variant A — Direct retrieval**
- **Variant B — Evidence-first**

The current evaluation runner processes the scenarios using retrieval and citation-metadata checks. The latest saved results report 20 scenarios processed and zero execution errors.

However, the runner does not execute either prompt variant. It does not calculate semantic evidence support, abstention accuracy, or overall scenario pass rate. Expected outcomes are also blank in the displayed scenario summary.

Consequently, the current results must be described as a retrieval evaluation run, not a completed 40-run prompt comparison. No unsupported evaluation scores are claimed in this report.

### 5. Limitations and Risks

The following limitations remain:

1. **Regulatory source verification:** The issuing authority, official source, document version, and current applicability have not been independently verified.
2. **Evidence support:** Citation verification checks citation structure and metadata, not whether a passage substantively supports a particular compliance conclusion.
3. **Multi-rule retrieval:** The workflow retrieves up to five clauses from a broad query. It has not been demonstrated to reliably retrieve every separately applicable requirement, including setback and road-width-dependent height or FAR rules.
4. **Conflict and escalation handling:** The current workflow does not demonstrate a dedicated decision branch for resolving conflicting rules or routing cases to a specialist.
5. **Evaluation completeness:** The two-prompt comparison and full scenario-level accuracy evaluation remain incomplete.
6. **Deployment and observability:** Full Docker Compose deployment, distributed tracing, monitoring dashboards, and load-test performance have not been established by the evidence reviewed here.

The service should therefore be presented as a preliminary evidence-retrieval and review-support prototype. Its output requires human verification before being relied upon for an actual building proposal.

### 6. Running the Project Locally

Activate the project's virtual environment and run the backend from the repository root:

```powershell
python -m uvicorn backend.app.main:app --reload
```

Run the frontend in a separate terminal:

```powershell
python -m http.server 5500 --directory frontend
```

Open the frontend at `http://127.0.0.1:5500`.

The backend is available at `http://127.0.0.1:8000`. Its interactive API documentation is normally available at `http://127.0.0.1:8000/docs`.

To rerun the automated tests:

```powershell
python -m pytest -q
```

To run the existing retrieval evaluation:

```powershell
python evaluation/run_evaluation.py
```

The evaluation command overwrites the existing results JSON file, so preserve a copy first if the previous results need to be retained.

### 7. Final Assessment

The project has a functioning core prototype, an integrated frontend and backend, a retrieval pipeline with source/page metadata, and a passing automated test suite.

The highest-priority next steps for a future iteration would be verifying the regulatory source, validating retrieval against the difficult multi-rule case, and executing a genuine comparison of both prompt variants against reviewed expected outcomes.

The current implementation is frozen for final review. No additional features or architectural changes are claimed as part of this finalization.

**Final test result: 23 passed in 7.84 seconds.**
