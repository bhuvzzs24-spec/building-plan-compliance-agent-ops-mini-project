\# Building Plan Compliance Pre-Check



A project for pre-checking building proposals against building bye-laws using a FastAPI backend, a RAG (Retrieval-Augmented Generation) pipeline, and ChromaDB vector storage.



\## Features



\- FastAPI endpoints for health checks, proposal validation, and compliance runs.

\- Input validation for required building proposal fields and positive numeric values.

\- Background processing with run IDs and status retrieval.

\- PDF indexing and text chunking for building bye-laws.

\- ChromaDB storage and retrieval of relevant passages with source and page metadata.

\- Generic error responses for unexpected compliance workflow failures.

\- Automated API, RAG, and evaluation configuration tests.



\## Technology Stack



\- Python

\- FastAPI

\- Pydantic

\- ChromaDB

\- Pytest

\- LangGraph workflow integration



\## Project Setup



\### 1. Clone the repository



```bash

git clone https://github.com/bhuvzzs24-spec/building-plan-compliance-agent-ops-mini-project.git

cd building-plan-compliance

```



If the cloned repository uses a different directory name, enter the directory created by Git.



\### 2. Create a virtual environment



\*\*Windows PowerShell\*\*



```powershell

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



\*\*macOS/Linux\*\*



```bash

python3 -m venv .venv

source .venv/bin/activate

```



\### 3. Install dependencies



```bash

python -m pip install -r requirements.txt

```



If dependency installation fails, check the Python version and the platform compatibility of the packages listed in `requirements.txt`.



\## Index Building Bye-Law PDFs



Place the source PDF files in the input directory expected by the indexing script, then run:



```bash

python -m agents.rag.index\_pdfs

```



The indexing process extracts PDF text, splits it into chunks, and stores the indexed passages in ChromaDB.



The current verified Windows environment contains a ChromaDB collection named `building\_bye\_laws` with 1,243 chunks. The configured persistent database path is `data/chroma\_db`.



\## Run the API



From the project root, run:



```bash

uvicorn backend.app.main:app --reload

```



The API should be available at:



\- API root: http://127.0.0.1:8000/

\- Health check: http://127.0.0.1:8000/health

\- Interactive API documentation: http://127.0.0.1:8000/docs



\## API Endpoints



| Method | Endpoint | Purpose |

|---|---|---|

| GET | `/` | Check that the API is running |

| GET | `/health` | Return API health status |

| POST | `/check` | Validate a building proposal |

| POST | `/runs` | Start a compliance run and return a run ID |

| GET | `/runs/{run\_id}` | Retrieve a run's status and results |



\### Example proposal



```json

{

&#x20; "building\_use": "Residential",

&#x20; "plot\_area": 240,

&#x20; "road\_width": 9,

&#x20; "proposed\_height": 12,

&#x20; "zone": "Residential"

}

```



Send this JSON body to `POST /check` or `POST /runs`.



The numeric values above are illustrative, not a declaration of compliance with any particular building regulation.



\## Run Tests



Run the complete test suite from the project root:



```bash

python -m pytest tests -q

```



To run individual test files:



```bash

python -m pytest tests/test\_api.py -q

python -m pytest tests/test\_rag.py -q

python -m pytest tests/test\_evaluation.py -q

```



The currently verified test suite passed with \*\*23 tests\*\* in the Windows development environment.



\## Evaluation



The evaluation configuration defines:

\- At least 20 unique scenarios.

\- Two prompt variants, A and B.

\- Five metrics: retrieval hit rate at 5, citation completeness, evidence support rate, abstention accuracy, and scenario pass rate.

\- A protocol specifying 40 prompt runs across 20 scenarios.



These are configured evaluation requirements. Completion of all 40 runs and calculation of every metric must be verified separately.



\## Current Limitations



\- Run state is stored in memory and may be lost when the API process restarts.

\- FastAPI background tasks are used; a durable external job queue has not been verified.

\- Retrieval results should be evaluated for relevance and citation evidence support.

\- Load testing and production deployment have not yet been verified.



\## Contributors



This is a collaborative college project. Contributions include frontend development, FastAPI backend implementation, RAG and ChromaDB indexing, workflow integration, citation verification, evaluation, and testing.
