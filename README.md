# Building Plan Compliance Pre-Check

A college project for pre-checking building proposals using a FastAPI backend, a retrieval-augmented generation (RAG) pipeline, LangGraph workflow integration, and ChromaDB vector storage.

> **Important:** This application is a pre-check prototype, not an official building approval system. A successful API response does not establish legal or regulatory compliance.

## Features

- FastAPI endpoints for health checks, proposal validation, and background compliance workflow runs.
- Input validation for required building proposal fields and positive numeric values.
- Background processing with run IDs and status retrieval.
- PDF indexing and text chunking for building bye-laws.
- ChromaDB storage and retrieval of passages with source and page metadata.
- Retrieval retry configuration and generic error responses for unexpected workflow failures.
- Automated API and RAG tests.
- Frontend and backend deployed on Render.

## Live Deployment

- **Frontend:** https://building-plan-compliance-frontend.onrender.com
- **Backend API:** https://building-plan-compliance-agent-ops-mini.onrender.com
- **API health check:** https://building-plan-compliance-agent-ops-mini.onrender.com/health
- **Interactive API documentation:** https://building-plan-compliance-agent-ops-mini.onrender.com/docs

The health endpoint reports whether the API process is responding. It does not by itself verify that the vector database, bye-law documents, or the full compliance workflow are ready.

## Technology Stack

- Python
- FastAPI and Uvicorn
- Pydantic
- LangGraph
- ChromaDB
- Pytest
- HTML, CSS, and JavaScript frontend

## Project Setup

### 1. Clone the repository

```bash
git clone https://github.com/bhuvzzs24-spec/building-plan-compliance-agent-ops-mini-project.git
cd building-plan-compliance-agent-ops-mini-project
```

If Git creates a directory with a different name, enter the directory it created.

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

If installation fails, check the Python version and platform compatibility of the packages listed in `requirements.txt`.

## Index Building Bye-Law PDFs

Place the source PDF files in the input directory expected by the indexing script, then run:

```bash
python -m agents.rag.index_pdfs
```

The indexing process extracts PDF text, splits it into chunks, and stores indexed passages in ChromaDB.

The verified Windows development environment previously contained a ChromaDB collection named `building_bye_laws` with 1,243 chunks. The configured persistent database path is `data/chroma_db`. These are local-environment observations and do not guarantee that the same collection or documents exist in the deployed service.

## Run the API Locally

From the project root, run:

```bash
uvicorn backend.app.main:app --reload
```

The API should be available at:

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Check that the API is responding |
| GET | `/health` | Return API health status |
| POST | `/check` | Validate proposal input and return findings; this endpoint does not itself perform a full regulatory compliance check |
| POST | `/runs` | Queue a background workflow run and return a run ID |
| GET | `/runs/{run_id}` | Retrieve a run's status and results |

### Example proposal

```json
{
  "building_use": "Residential",
  "plot_area": 240,
  "road_width": 9,
  "proposed_height": 12,
  "zone": "Residential"
}
```

Send this JSON body to `POST /check` or `POST /runs`.

The values are illustrative only. They do not represent verified limits or compliance with any particular building regulation.

### Background runs

`POST /runs` returns a run ID. Use that ID with `GET /runs/{run_id}` to retrieve the current status and any available findings, clauses, or citations. A run may initially be `pending` or `running`, and may later complete or fail.

## Run Tests

Run the complete test suite from the project root:

```bash
python -m pytest tests -q
```

For the Windows virtual environment used during development:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Individual test files can be run with:

```bash
python -m pytest tests/test_api.py -q
python -m pytest tests/test_rag.py -q
python -m pytest tests/test_evaluation.py -q
```

**Latest recorded test result during development:** 23 tests passed. Run the suite again after making changes to confirm the current result.

## Evaluation

The evaluation configuration defines:

- At least 20 unique scenarios.
- Two prompt variants, A and B.
- Five metrics: retrieval hit rate at 5, citation completeness, evidence support rate, abstention accuracy, and scenario pass rate.
- A protocol specifying 40 prompt runs across 20 scenarios.

These are configured evaluation requirements. Completion of all 40 runs and calculation of every metric must be verified separately.

## Reliability and Safety Notes

- The workflow retrieval node is configured with a retry policy of up to three attempts.
- Unexpected workflow exceptions are returned as a generic failure message rather than exposing internal exception details.
- Workflow waiting is bounded by a 30-second timeout in the background-run handler. A Python worker thread may continue running after the wait times out; this timeout is not hard cancellation.
- Run records are held in process memory and may be lost when the API restarts. They are not backed by a durable job queue or persistent run database.
- The `/health` endpoint checks API responsiveness, not full dependency readiness.
- Citation metadata checks do not, by themselves, prove that a cited passage legally supports a compliance conclusion.
- Regulatory rules, retrieved evidence, and citations require domain review before results can be relied upon for real building decisions.
- A basic smoke test previously recorded 20 sequential successful `GET /health` responses (`200 OK`). This was not a concurrent load test or a production performance test.

## Current Limitations

- This is a prototype for pre-checking proposals, not a replacement for review by qualified professionals or the relevant authority.
- The `/check` endpoint validates the proposal fields but does not itself run the full regulatory workflow.
- Background run state is in memory and is not durable across process restarts.
- Timed-out workflow threads may continue executing in the background.
- Retrieval relevance, evidence support, and legal accuracy need further evaluation.
- Deployment URLs are provided above, but deployed data availability and full workflow readiness must be checked independently.

## Contributors

This is a collaborative college project. Contributions include frontend development, FastAPI backend implementation, RAG and ChromaDB indexing, workflow integration, citation verification, evaluation, testing, and deployment.
