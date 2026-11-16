# Local Website Verification Report

**Date:** 17 November 2026
**Status:** **NOT READY for a browser-verified faculty demonstration**

## Local startup and service checks

Started the requested command:

```bash
./scripts/start_local.sh
```

The launcher reused the existing local index: 243 chunks from the historical PDF, 243 reused and 0 rebuilt. It started FastAPI at `127.0.0.1:8000` and the frontend at `localhost:5500` with Redis disabled and the in-process worker fallback enabled.

Observed service checks:

| Check | Result |
|---|---|
| `GET /health` | HTTP 200, API healthy |
| `GET /health/ready` | HTTP 200, 243 indexed chunks |
| Frontend `/` | HTTP 200 |
| Frontend `/app.js` | HTTP 200 |
| Frontend `/style.css` | HTTP 200 |
| API `/metrics` | HTTP 200 in the current code path (earlier local smoke); not a browser check |

## API integration checks (not browser UI checks)

- Valid proposal: `POST /runs` returned HTTP 202/pending; polling reached HTTP 200/completed. The API returned 10 findings, 17 citations, and `specialist-review` due the historical corpus's currentness/applicability limits.
- Invalid proposal (`building_use=invalid`, `plot_area=-1`): HTTP 422 with field-level validation errors, quarantine ID, and `agent_started=false`.
- Backend logs recorded the submitted correlation ID, successful completion, and quarantine event. No workflow failure occurred in this run.

These checks exercise the API and local workflow. They do **not** demonstrate that the browser form submitted the request or rendered the results.

## Browser automation attempt and blocker

Browser-driven form submission, validation display, navigation/button interaction, browser console inspection, and browser network inspection are **BLOCKED**:

- Available space reported by `df -h .`: 2.4 GiB.
- Python Playwright, Selenium, and Pyppeteer are not installed. Node Playwright/Puppeteer packages are also unavailable.
- Installed Google Chrome reports version 157.0.8103.52. Headless launches exit immediately with code 134. The GUI launch did not expose a Chrome DevTools Protocol endpoint. The first Chrome app bundle on disk is incomplete and macOS reports its executable missing.
- Safari and `safaridriver` are installed. `safaridriver --port 4444` exits with code 1 until remote automation is enabled. `safaridriver --enable` requested administrator authentication; no password was supplied and no privileged system setting was changed.
- No browser package or browser binary was installed or downloaded.

Because there was no controllable browser session, no actual form submit, result rendering, invalid-form display, click/navigation test, browser console capture, or browser-originated request capture was performed. Static HTML/JS inspection and HTTP resource checks do not substitute for these checks.

## Automated validation

- `python3 -m pytest -q` — **PASS: 47 passed in 1.73s**.
- `node --check frontend/app.js` — **PASS**.
- Local API and static resource HTTP checks — **PASS**, as listed above.

## What is needed to finish the website demonstration check

Run browser automation on this machine after Safari Remote Automation has been enabled by an administrator (or use a machine with an already working Playwright/Selenium browser runtime). Then submit both valid and invalid proposals, verify rendered results and citations, exercise navigation and all visible controls, inspect console/network activity, and record the browser session before marking the website ready.
