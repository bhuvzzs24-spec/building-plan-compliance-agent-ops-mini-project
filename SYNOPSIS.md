# Project Synopsis
## Building Plan Compliance Pre-Check Service
### AgentOps Mini Project 05

## 1. Abstract

Building-plan approval requires checking proposed construction details against applicable building regulations, including requirements related to setbacks, road width, building height, floor area ratio (FAR), plot coverage, and permitted land use. Reviewing these requirements manually can be time-consuming, particularly when relevant provisions are distributed across lengthy building bye-law documents.

The **Building Plan Compliance Pre-Check Service** is a prototype decision-support application designed to assist with the preliminary examination of building proposals. The system accepts structured building and site information, retrieves potentially relevant provisions from an indexed collection of building-rule PDF documents, verifies that returned citations correspond to stored source passages, and presents the evidence and review status to the user. It uses a FastAPI backend and a LangGraph-based workflow to coordinate the retrieval and verification stages. A web interface supports submitting proposals and viewing the resulting run information.

The application is deliberately designed to route results for specialist review rather than issue final compliance clearance. Citation verification confirms that a passage exists in the indexed collection; it does not establish that the provision is legally current, applicable to a particular property, or sufficient to determine compliance. The project demonstrates how retrieval workflows, validation, traceability, testing, and operational monitoring can be combined in an AgentOps-oriented application.

## 2. Introduction

Building regulations define conditions that proposed construction must satisfy. These conditions can vary according to location, building use, plot dimensions, road width, zoning, and other site characteristics. Finding the relevant clauses in regulatory documents and comparing them with a proposal requires careful review.

This project introduces a software-based pre-check workflow to organise this process. Instead of treating a generated answer as an approval decision, the system focuses on collecting structured proposal data, identifying relevant regulatory evidence, checking citation references, and making the review process traceable. The application combines document retrieval with a controlled agent workflow and supporting operational components.

## 3. Problem Statement

Manual preliminary checking of building proposals against building bye-laws can require considerable time and effort. Relevant provisions may be distributed across multiple pages or sections of lengthy PDF documents. It can also be difficult to trace a conclusion back to the exact source passage used.

A system is therefore needed to accept structured building details, search for relevant regulatory evidence, verify the location and text of citations, and clearly identify cases that require human assessment. The system must avoid presenting incomplete retrieval results or historical regulatory documents as definitive proof of legal compliance.

## 4. Objectives

The main objectives of the project are:

1. To develop a web-based service for submitting structured building proposal information.
2. To validate proposal fields and reject incomplete, invalid, or out-of-range inputs before starting the agent workflow.
3. To index building bye-law PDF documents with source and page metadata.
4. To retrieve potentially relevant provisions for different compliance-related dimensions, such as setbacks, road width and height, FAR, plot coverage, and permitted use.
5. To verify retrieved citations against the exact stored source, page, and passage.
6. To maintain traceable run records, correlation identifiers, and workflow tool traces.
7. To provide a feedback mechanism and operational visibility through logging, metrics, and dashboards.
8. To route results requiring interpretation or confirmation to a qualified specialist instead of issuing automatic approval.

## 5. Scope of the Project

The prototype focuses on preliminary evidence retrieval and review support. It accepts information such as building use, plot area, road width, proposed height, zone, and optional site dimensions, proposed coverage, and FAR.

The workflow searches the indexed document collection for relevant provisions and returns evidence items, citation information, verification limits, and a review route. The application also includes input validation, run-status retrieval, rejection metadata, feedback recording, automated tests, retrieval evaluation, load-test configuration, and monitoring infrastructure.

The current implementation is not intended to replace architects, licensed professionals, planning authorities, or statutory approval procedures. It does not certify that a proposal complies with all applicable laws.

## 6. Proposed Methodology

The system follows a sequence of input validation, document retrieval, evidence verification, and review routing.

### 6.1 Proposal Submission and Validation

The user submits building details through the frontend. The FastAPI backend validates required fields, accepted categories, numeric ranges, and dimensional constraints. Invalid submissions are rejected before the agent workflow begins. Rejection metadata records a payload hash and field-level errors rather than retaining the original invalid proposal body.

### 6.2 Regulatory Document Processing

Building bye-law PDFs are placed in the project's document corpus. The indexing pipeline extracts page text, divides it into smaller chunks, and retains source and page metadata. It generates local deterministic hashed word, bigram, and trigram representations and stores the indexed chunks in ChromaDB. An index manifest records source hashes and indexing information.

### 6.3 Agent-Based Retrieval Workflow

A LangGraph workflow coordinates three main responsibilities:

- **Retrieval Planner Agent:** Examines the submitted proposal fields and plans targeted searches for relevant regulatory obligations.
- **Provision Discovery Agent:** Selects and invokes corpus-search tools to find potentially relevant provisions and citation locations. The workflow limits tool calls and execution time.
- **Evidence Verification Agent:** Checks whether each citation resolves to the expected stored source, page, and text, then determines the appropriate review route.

The workflow uses tools for looking up request fields, searching the indexed corpus, and locating clauses by document location.

### 6.4 Result Generation and Review Routing

After retrieval and verification, the service records the findings, evidence items, citations, workflow trace, correlation ID, and verification limitations. Results are routed to specialist review. Missing evidence, incomplete site information, and uncertain applicability are not treated as approval.

### 6.5 Feedback and Monitoring

The service stores user feedback and provides an aggregated feedback summary. Structured application logs and Prometheus-compatible metrics support monitoring. Grafana dashboards provide a visual view of operational information. Redis supports queued jobs in the Docker Compose deployment, while persistent run and feedback records are stored in a shared SQLite volume.

## 7. System Architecture and Technologies Used

The application is organised into the following components:

| Component | Technology / Responsibility |
|---|---|
| Backend API | Python and FastAPI |
| Agent orchestration | LangGraph |
| Document parsing and indexing | PDF processing pipeline with page and source metadata |
| Vector storage | ChromaDB |
| Retrieval representation | Local deterministic hashed word, bigram, and trigram features |
| Job queue | Redis |
| Run and feedback persistence | SQLite |
| Frontend | Static web interface |
| Containerisation | Docker and Docker Compose |
| Monitoring and metrics | Prometheus and Grafana |
| Automated testing | pytest |
| Load-testing configuration | Locust |

The Docker Compose setup coordinates the API, worker, Redis service, corpus indexing, frontend, Prometheus, and Grafana. The API also exposes endpoints for health checks, readiness, proposal validation, run submission and status, quarantine metadata, feedback, and metrics.

## 8. Expected Outcomes

The expected outcome is a working prototype that demonstrates how building proposal information can be validated and used to retrieve traceable regulatory evidence. The system is expected to:

- Accept valid structured building proposals and reject invalid submissions with clear field-level errors.
- Search the indexed regulatory corpus for potentially relevant provisions.
- Associate retrieved evidence with source and page information.
- Verify that citation references resolve to stored passages.
- Provide run status, findings, workflow traces, and verification limitations.
- Route results for professional review instead of issuing unsupported compliance clearance.
- Provide a foundation for testing, feedback collection, and operational monitoring.

The repository includes an evaluation runner for retrieval and citation metadata and a Locust load-test configuration. Performance targets and test configurations should not be interpreted as measured results unless corresponding test runs have been executed and recorded.

## 9. Limitations

The current prototype has several important limitations:

1. The indexed regulatory corpus is historical and is not confirmed to be the complete or current set of regulations applicable to a property.
2. Citation resolution confirms that text exists in the indexed collection; it does not prove legal currentness, semantic support, or applicability.
3. The retrieval approach uses a deterministic local lexical baseline, so retrieval relevance requires further evaluation.
4. The system does not establish that every relevant provision or possible conflict has been identified.
5. It does not assess every site-specific or architectural dimension required for a formal building approval.
6. The current evaluation runner focuses on retrieval and citation metadata; it does not establish semantic groundedness, faithfulness, or hallucination rates.
7. Load-test and worker-scaling outcomes must be measured before performance claims can be made.

Consequently, every run is routed for specialist review, and the application must not be used as a substitute for official regulatory verification or approval.

## 10. Future Enhancements

Possible future improvements include:

- Expanding and regularly reviewing the regulatory corpus using authoritative, current documents and amendments.
- Improving retrieval quality and evaluating it against a larger, reviewed set of test cases.
- Adding semantic evidence-support and groundedness evaluation.
- Detecting conflicting provisions and improving applicability checks using location and zoning information.
- Introducing stronger audit and observability capabilities, including distributed tracing and resource-level monitoring.
- Conducting and documenting load, reliability, and worker-scaling experiments.
- Improving feedback-driven evaluation and the review interface.
- Integrating the system with verified professional review workflows while retaining human oversight.

These are proposed enhancements and should not be described as completed features unless implemented and tested.

## 11. Conclusion

The Building Plan Compliance Pre-Check Service demonstrates an AgentOps-oriented approach to preliminary building-rule evidence retrieval. By combining structured input validation, PDF indexing, a LangGraph workflow, citation verification, persistent run records, feedback, and monitoring, the prototype aims to make preliminary regulatory research more organised and traceable.

Its central design principle is to distinguish evidence retrieval from a legal compliance decision. The system provides supporting information and explicitly routes results for specialist review, helping avoid unsupported automated approvals. With an updated regulatory corpus, stronger retrieval evaluation, and further validation, the prototype can serve as a foundation for a more comprehensive building-plan review support system.

---

**Repository:** https://github.com/bhuvzzs24-spec/building-plan-compliance-agent-ops-mini-project

**Project category:** AgentOps / AI-assisted regulatory evidence retrieval and decision support
