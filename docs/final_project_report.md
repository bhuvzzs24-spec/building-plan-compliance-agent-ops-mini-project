# Building Plan Compliance Pre-Check Service

## Final Project Report

**Repository:**
[building-plan-compliance-agent-ops-mini-project](https://github.com/bhuvzzs24-spec/building-plan-compliance-agent-ops-mini-project)\
**Report purpose:** Final summary of the implemented prototype,
architecture, testing, evaluation status, limitations, and run
instructions.

------------------------------------------------------------------------

## 1. Executive Summary

The Building Plan Compliance Pre-Check Service is a prototype that helps
a user conduct a preliminary review of proposed building details by
retrieving potentially relevant building bye-law passages and displaying
them with source and page citations.

The project combines a FastAPI backend, a browser-based frontend, a
LangGraph workflow, PDF processing, and a ChromaDB vector store. The
workflow validates core building inputs, retrieves clauses from the
indexed corpus, and checks that returned citations have basic
traceability metadata. When evidence cannot be retrieved or traced, the
workflow indicates that manual review is required.

The final automated test run reported **23 passed in 7.84 seconds**. The
frontend and backend integration and the display of clauses/citations
were also manually confirmed by the developer.

This is an evidence-retrieval and preliminary review prototype. It is
**not** a certified building-plan approval system, and the retrieved
regulations' current legal applicability has not been independently
verified.

## 2. Problem Statement and Scope

Building-plan pre-checking involves comparing proposed building details
with relevant regulatory requirements. Relevant rules may be distributed
across different parts of a bye-law document, and a useful review result
should make its evidence traceable to a source and page.

The project aims to provide a local service that accepts structured
building details, retrieves potentially relevant passages from a PDF
corpus, and presents the results for human review.

### In scope

-   REST API endpoints for health, validation, and asynchronous-style
    run/result handling.
-   Validation of required building fields and basic numeric
    constraints.
-   PDF ingestion, text chunking, indexing, and retrieval using
    source/page metadata.
-   Workflow integration using LangGraph.
-   Citation metadata checks and manual-review findings when evidence is
    missing.
-   Browser frontend for submitting a proposal and viewing results.
-   Automated tests for API behavior, evaluation configuration, and RAG
    behavior.

### Out of scope or not demonstrated as complete

-   CAD or building-plan drawing/PDF interpretation.
-   Authoritative legal advice or automatic approval of a building
    proposal.
-   Independent verification that the indexed regulation is the current
    official version applicable to a property.
-   A completed two-prompt, 40-run evaluation.
-   Full production deployment, distributed observability, and
    load/scaling measurements.

## 3. Architecture and Components

The project is organized into the following main areas:

  ----------------------------------------------------------------------------
  Component               Location                     Responsibility
  ----------------------- ---------------------------- -----------------------
  API                     `backend/app/main.py`        FastAPI application and
                                                       API routes

  Workflow                `agents/workflow.py`         Validation, retrieval,
                                                       and citation
                                                       verification steps

  PDF indexing            `agents/rag/index_pdfs.py`   Finds PDFs in the
                                                       bye-law corpus
                                                       directory and invokes
                                                       indexing

  Indexer and PDF         `agents/rag/`                PDF loading, text
  processing                                           chunking, indexing,
                                                       vector storage, and
                                                       retrieval

  Regulation corpus       `data/bye_laws/`             Building bye-law PDF
                                                       used by the prototype

  Vector database         `data/chroma_db/`            Local ChromaDB
                                                       persistence

  Frontend                `frontend/`                  Browser interface for
                                                       submitting a check and
                                                       displaying results

  Evaluation              `evaluation/`                Scenario dataset,
                                                       runner, and saved
                                                       retrieval results

  Automated tests         `tests/`                     API, evaluation, and
                                                       RAG tests

  Documentation           `README.md`, `docs/`         Setup, source notes,
                                                       and review
                                                       documentation
  ----------------------------------------------------------------------------

### Request flow

1.  The user submits structured building details through the frontend or
    API.
2.  The API validates the request and creates or processes a run.
3.  The LangGraph workflow checks required fields and basic numeric
    constraints.
4.  The retrieval node searches the indexed corpus for potentially
    relevant clauses.
5.  The citation-verification node checks whether retrieved clauses have
    non-empty text, a source, and a positive integer page number.
6.  The API returns the run status, findings, clauses, and citations for
    display.
7.  If retrieval fails or traceable evidence is absent, the workflow
    adds a manual-review finding.

### Workflow nodes

`agents/workflow.py` defines three nodes:

-   `validate_building_details`
-   `retrieval_agent`
-   `citation_verification_agent`

The retrieval node has a LangGraph `RetryPolicy` configured with
`max_attempts=3`. The graph currently connects these nodes sequentially
and then ends.

## 4. API and Frontend

The README documents these API routes:

  Route                  Purpose
  ---------------------- -------------------------------------
  `GET /`                Basic application/root response
  `GET /health`          Health check
  `POST /check`          Validation-only check
  `POST /runs`           Start a compliance-check run
  `GET /runs/{run_id}`   Retrieve the status/result of a run

The frontend is served separately during local development. The frontend
JavaScript submits a run, polls for its result, and displays the
returned status, building details, findings, clauses, citations, and
source pages. A disclaimer is also shown.

The developer manually confirmed that the frontend and backend worked
together and that clauses and citations appeared in the interface. The
automated test suite also covers API behavior, but a passing test suite
does not prove every real-world compliance case is handled correctly.

## 5. Retrieval and Citation Handling

The indexing script `agents/rag/index_pdfs.py` searches `data/bye_laws`
for PDF files and calls the indexer for each file, using
`data/chroma_db` as the database directory. Errors are printed for
individual files so the script can continue attempting the remaining
PDFs.

The retrieval workflow calls `retrieve_clauses` with `top_k=5`. Returned
clauses are passed to the citation-verification node, which checks basic
metadata requirements:

-   Passage text is non-empty.
-   Source is a non-empty string.
-   Page is a positive integer and is not a Boolean value.

If no traceable citations remain, the workflow adds a finding that
manual review is required.

These checks establish citation structure and traceability only. They do
not verify that a passage semantically supports a particular claim, that
all relevant rules were retrieved, or that the rule is legally current.

## 6. Evaluation

### Dataset

The existing `evaluation/sloka_evaluation.json` contains:

-   20 scenarios.
-   Two defined prompt variants: **Direct retrieval** and
    **Evidence-first**.
-   A protocol specifying 40 total prompt runs if each scenario is
    executed with both variants.
-   Planned fields for retrieved passages, source/page, expected and
    actual outcomes, citation completeness, evidence support,
    manual-review need, and pass/fail.

The scenarios cover questions about setbacks, plot area, road width,
height, FAR, ground coverage, parking, zoning, missing evidence,
citation traceability, conflicting passages, out-of-scope questions,
document applicability, authority, invalid inputs, multi-rule retrieval,
evidence sufficiency, and an empty vector collection.

### What was actually executed

The current `evaluation/run_evaluation.py` executes retrieval for each
scenario and records retrieval counts, a source-name hit proxy when
expected source names are provided, and citation metadata completeness.
The saved result file reported:

-   Scenarios in dataset: 20.
-   Scenarios processed: 20.
-   Scenarios with errors: 0.

### Evaluation limitations

The runner explicitly does not execute either prompt template or call an
LLM to compare prompt variants. The scenario list shown during review
has no populated expected outcomes/source expectations. Evidence
support, abstention accuracy, and overall scenario pass rate are not
calculated; those fields are recorded as unavailable.

Therefore, this project does **not** claim to have completed the
specified 40 prompt runs or a semantic compliance-accuracy evaluation.
The current output should be described as a retrieval and
citation-metadata check, not as proof of legal correctness.

## 7. Testing Results

The final test command was:

``` powershell
python -m pytest -q
```

Observed result:

``` text
.......................                                                  [100%]
23 passed in 7.84s
```

The test files are:

-   `tests/test_api.py`
-   `tests/test_evaluation.py`
-   `tests/test_rag.py`

The tests cover API behavior, evaluation configuration, and RAG
indexing/retrieval/citation behavior. The exact coverage of each
individual requirement should be interpreted from the tests themselves;
the total passing count is not evidence that all assignment requirements
are implemented.

The developer also confirmed that the frontend could submit a request
and display results, including clauses and citations.

## 8. Local Setup and Run Instructions

Run commands from the repository root in PowerShell. Activate the
project's virtual environment first.

### Start the backend

``` powershell
python -m uvicorn backend.app.main:app --reload
```

The backend is expected at `http://127.0.0.1:8000`. The interactive API
documentation is normally available at `http://127.0.0.1:8000/docs`.

### Start the frontend

In a separate terminal, from the repository root:

``` powershell
python -m http.server 5500 --directory frontend
```

Open `http://127.0.0.1:5500` in a browser.

### Run the tests

``` powershell
python -m pytest -q
```

### Run the existing retrieval evaluation

``` powershell
python evaluation/run_evaluation.py
```

This evaluation command writes to
`evaluation/sloka_evaluation_results.json`, replacing the previous
contents. Preserve a copy first if you need to retain an earlier run.

### Rebuild the local PDF index

Place the intended PDF corpus in `data/bye_laws/`, then run:

``` powershell
python -m agents.rag.index_pdfs
```

Review the script output and verify that the intended PDF files were
indexed successfully. Indexing completion by itself does not verify the
legal currency or completeness of the corpus.

## 9. Known Limitations and Risks

1.  **Source authority and currency:** The project completion notes
    identify verification of the issuing authority, official source URL,
    document title/version, and current applicability as pending.
2.  **Exact legal rules:** The exact setback, minimum plot area,
    road-width, height, FAR, and ground-coverage requirements have not
    been independently verified in this review.
3.  **Semantic support:** Citation checks validate metadata structure,
    not whether the cited passage entails the conclusion.
4.  **Multi-rule retrieval:** A single broad query retrieves up to five
    clauses. The workflow does not explicitly guarantee retrieval of
    each separately applicable requirement, such as both setback limits
    and a road-width-dependent height/FAR rule.
5.  **Conflicting rules and specialist routing:** A dedicated branch for
    resolving conflicting provisions or routing exemptions and
    unsupported cases to a specialist was not demonstrated in the
    reviewed workflow.
6.  **Evaluation completeness:** The prompt variants are defined but not
    executed by the current runner; expected outcomes are not populated
    in the reviewed scenario summary.
7.  **Operational infrastructure:** Docker Compose services, distributed
    tracing, monitoring dashboards, a genuine incident log, and
    load-test results were not established by the evidence reviewed for
    this report.
8.  **Run-state and timeout behavior:** The README describes in-process
    run state and a timeout approach. These should not be interpreted as
    a durable queue or proof that background work is always cancelled
    after a timeout.
9.  **Regulatory disclaimer:** Results should be manually checked
    against the official applicable rules before any real submission or
    decision.

## 10. Prioritization and Design Decisions

The project prioritizes a locally runnable core prototype: API,
workflow, PDF-based retrieval, citation metadata, frontend integration,
and automated tests.

The current implementation uses ChromaDB for local vector persistence
and LangGraph to connect workflow steps. The retrieval workflow uses a
bounded number of returned clauses and a configured retry policy for the
retrieval node.

At final review, the decision was to avoid broad late-stage rewrites and
preserve the passing baseline. Remaining gaps are documented rather than
represented as completed functionality. This is a scope-control
decision, not a claim that every assignment item has been satisfied.

## 11. Final Status

### Verified in the available project evidence

-   FastAPI application and documented endpoints exist.
-   Frontend/backend integration was manually confirmed by the
    developer.
-   PDF indexing and retrieval components are present.
-   The workflow validates required fields and basic numeric values.
-   The workflow checks basic source/page citation metadata.
-   The final automated test run passed all 23 tests.
-   The final review report was committed and pushed to the GitHub
    `main` branch.
-   Git status was confirmed clean and synchronized with `origin/main`.

### Not verified as complete

-   Full two-prompt comparison over 40 runs.
-   Semantic evidence support and scenario-level compliance accuracy.
-   Official source and current legal applicability of the corpus.
-   Guaranteed retrieval of all relevant rules for the difficult
    multi-rule case.
-   Full Docker Compose, observability, scaling, and load-test
    requirements.

### Conclusion

The Building Plan Compliance Pre-Check Service is a working prototype
for retrieving and presenting potentially relevant building bye-law
evidence. Its core test suite passes and its frontend/backend flow has
been manually exercised. It should be presented as a preliminary review
aid with explicit human-verification requirements---not as an
authoritative compliance decision system.

**Final recorded test result: 23 passed in 7.84 seconds.**
