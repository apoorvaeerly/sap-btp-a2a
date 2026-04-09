# Tests — A2A Validation Suite

This folder contains the full test suite for validating the SAP BTP A2A integration — from raw AI Core credentials through to the complete bidirectional agent communication flow.

Run tests in order when setting up from scratch. Each test builds on the previous one.

---

## Test Overview

| Test | What it validates | Run when |
|---|---|---|
| `test_token_at.py` | SAP AI Core OAuth token flow | First — before anything else |
| `test_completion.py` | SAP AI Core GPT-4.1 completions | After token test passes |
| `test_e2e.py` | Full A2A flow — both directions | After both agents are running |

---

## Prerequisites

Before running any tests:

- Virtual environment activated
- `.env` file configured at project root with all AI Core credentials
- For `test_e2e.py` specifically:
  - Eerly Studio running: `uvicorn agent.eerly_studio.api:app --port 8000 --reload`
  - Joule persona running: `uvicorn joule_persona.api:app --port 8001 --reload`
  - ngrok tunnel active and `AGENT_BASE_URL` updated in `.env`

Always run tests from the **project root** (`sap-btp-a2a/`), not from inside the `tests/` folder.

---

## test_token_at.py — OAuth Token Test

### What it tests

Validates the complete OAuth2 Client Credentials flow against SAP AI Core. This is the foundation — if this fails, nothing else will work.

### How to run

```bash
python tests/test_token_at.py
```

### Expected output

```
Status code: 200
Response: {'access_token': 'eyJhbGci...', 'token_type': 'bearer', 'expires_in': 43199}
```

### What success means

- `AI_CORE_CLIENT_ID`, `AI_CORE_CLIENT_SECRET`, and `AI_CORE_AUTH_URL` are all correct
- SAP's UAA auth server is reachable
- The service key JSON was extracted correctly

### Common failures

| Error | Cause | Fix |
|---|---|---|
| `Status code: 401` | Wrong client ID or secret | Re-check service key JSON — copy values exactly |
| `Status code: 302` with redirect to `invalid_login_request` | `!` characters corrupted by Windows CMD | Use Python script instead of curl |
| `ConnectionError` | Wrong `AI_CORE_AUTH_URL` | Confirm URL ends with `/oauth/token` |

---

## test_completion.py — AI Core Completions Test

### What it tests

Sends a real prompt to SAP AI Core GPT-4.1 and validates the response. Confirms the full pipeline: OAuth token → deployment discovery → chat completions.

### How to run

```bash
python tests/test_completion.py
```

### Expected output

```
Deployment ID: dfd6008eecb87204
API URL: https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com
Token acquired successfully
Endpoint: https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com/v2/inference/deployments/dfd6008eecb87204/chat/completions?api-version=2024-02-01
Resource Group: default
Status code: 200
Response: {'choices': [{'message': {'content': 'SAP AI Core is...'}}], ...}
```

### What success means

- `AI_CORE_API_URL` and `AI_CORE_DEPLOYMENT_ID` are correct
- The deployment is in **Running** status in AI Launchpad
- GPT-4.1 is responding to prompts correctly

### Common failures

| Error | Cause | Fix |
|---|---|---|
| `Status code: 404` with `deployment/None/` in URL | `AI_CORE_DEPLOYMENT_ID` missing from `.env` | Add the deployment ID to `.env` |
| `Status code: 404` with correct deployment ID | Missing `?api-version=2024-02-01` | Confirm the endpoint URL includes the api-version query parameter |
| `Status code: 404` with `Resource not found` | Deployment is stopped or wrong deployment ID | Go to AI Launchpad → Deployments → confirm status is Running |

---

## test_e2e.py — Full A2A End-to-End Test

### What it tests

The complete bidirectional A2A flow:

- **Direction 1 (Eerly Studio):** 3 test cases covering valid SAP questions, SAP AI Core questions, and out-of-scope rejection
- **Direction 2 (Joule persona):** 3 test cases covering valid SAP S/4HANA questions, Eerly awareness, and out-of-scope rejection

### How to run

```bash
python tests/test_e2e.py
```

### Expected output

```
A2A End-to-End Test Suite
Eerly Studio : https://your-ngrok-url.ngrok-free.dev
Joule persona: http://localhost:8001
Timeout      : 60s

Step 1 — Health checks
  Eerly Studio reachable at https://your-ngrok-url.ngrok-free.dev
  Joule persona reachable at http://localhost:8001

Direction 1 — Eerly Studio (SAP Expert proxy)
[PASS] E01 — Valid SAP BTP question
[PASS] E02 — Valid SAP AI Core question
[PASS] E03 — Out of scope — should be rejected by Eerly [rejection expected]

Direction 2 — SAP Joule persona (Joule stand-in)
[PASS] J01 — Valid SAP S/4HANA question
[PASS] J02 — Joule awareness of Eerly Studio
[PASS] J03 — Out of scope — should be rejected by Joule [rejection expected]

Summary
  Direction 1 — Eerly Studio : 3/3 passed
  Direction 2 — Joule persona: 3/3 passed
  Total                      : 6/6 passed

All tests passed.
Both A2A directions are operational and ready for demo.
To swap in real agents: update AGENT_BASE_URL / JOULE_BASE_URL in .env
```

### Test case reference

#### Direction 1 — Eerly Studio

| ID | Question | Expected behaviour |
|---|---|---|
| E01 | What is SAP BTP and what are its core services? | Full SAP BTP explanation |
| E02 | How does SAP AI Core integrate with the Generative AI Hub? | Detailed AI Core + Gen AI Hub explanation |
| E03 | Who won the FIFA World Cup in 2022? | Rejection — out of SAP domain |

#### Direction 2 — Joule persona

| ID | Question | Expected behaviour |
|---|---|---|
| J01 | What are the key differences between SAP S/4HANA Cloud and On-Premise? | Detailed S/4HANA comparison |
| J02 | What is Eerly AI Studio and how does it relate to SAP BTP? | Acknowledgement of Eerly as A2A partner |
| J03 | What is the best programming language to learn in 2025? | Rejection — out of SAP domain |

### Common failures

| Failure | Cause | Fix |
|---|---|---|
| `Health check failed — Eerly Studio` | Uvicorn not running on port 8000 | Start: `uvicorn agent.eerly_studio.api:app --port 8000 --reload` |
| `Health check failed — Joule persona` | Uvicorn not running on port 8001 | Start: `uvicorn joule_persona.api:app --port 8001 --reload` |
| `[sandbox] HTTP 404` on Eerly tests | ngrok URL changed or stale | Restart ngrok, update `AGENT_BASE_URL` in `.env` |
| `[sandbox] Request timed out` | AI Core too slow for 30s timeout | Set `AGENT_TIMEOUT=60` in `.env` |
| `Aborting — one or more agents unreachable` | Agent health check failed | Fix the unreachable agent first, then re-run |

---

## Running All Tests in Sequence

Use this sequence when setting up from scratch or validating after a break:

```bash
# Step 1 — credentials only
python tests/test_token_at.py

# Step 2 — AI Core pipeline
python tests/test_completion.py

# Step 3 — start agents (in separate windows)
# Window 1: uvicorn agent.eerly_studio.api:app --port 8000 --reload
# Window 2: uvicorn joule_persona.api:app --port 8001 --reload
# Window 3: ngrok\ngrok.exe http 8000  (then update AGENT_BASE_URL in .env)

# Step 4 — bridge adapters in isolation
python bridge/test_adapter.py

# Step 5 — full E2E
python tests/test_e2e.py
```

If any step fails, fix it before proceeding to the next. Each test is a dependency for the one after it.

---

## Environment Variables Used by Tests

| Variable | Used by | Purpose |
|---|---|---|
| `AI_CORE_CLIENT_ID` | `test_token_at.py`, `test_completion.py` | OAuth client ID |
| `AI_CORE_CLIENT_SECRET` | `test_token_at.py`, `test_completion.py` | OAuth client secret |
| `AI_CORE_AUTH_URL` | `test_token_at.py`, `test_completion.py` | Token endpoint |
| `AI_CORE_API_URL` | `test_completion.py` | AI API base URL |
| `AI_CORE_DEPLOYMENT_ID` | `test_completion.py` | GPT-4.1 deployment ID |
| `AI_CORE_RESOURCE_GROUP` | `test_completion.py` | Defaults to `default` |
| `AGENT_BASE_URL` | `test_e2e.py` | Eerly Studio ngrok URL |
| `JOULE_BASE_URL` | `test_e2e.py` | Joule persona URL |
| `AGENT_TIMEOUT` | `test_e2e.py` | Request timeout in seconds |

---

## Adding New Test Cases to test_e2e.py

To add a new test case, append to the relevant list in `test_e2e.py`:

```python
EERLY_TESTS = [
    ...
    {
        "id":            "E04",
        "description":   "SAP Integration Suite question",
        "message":       "What is SAP Integration Suite used for?",
        "expect_reject": False,
    },
]
```

Fields:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID — E prefix for Eerly, J prefix for Joule |
| `description` | `str` | Human-readable description shown in output |
| `message` | `str` | The question sent to the agent |
| `expect_reject` | `bool` | If True, adds `[rejection expected]` label to output |