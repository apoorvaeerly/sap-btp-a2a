# SAP BTP A2A — Bidirectional Agent-to-Agent Integration

A modular, production-ready sandbox demonstrating bidirectional **Agent-to-Agent (A2A)** communication between **Eerly AI Studio** and **SAP Joule**, built on **SAP BTP** with **SAP AI Core** and **GPT-4.1**.

---

## What This Repository Demonstrates

This repo implements the **Google A2A protocol concept** — a standard for agents to discover, communicate with, and delegate tasks to other agents over HTTP.

Two directions are demonstrated:

| Direction | Flow | Status |
|---|---|---|
| Direction 1 | User types `@joule` inside Eerly Studio → routes to Joule agent | ✅ Working (persona stand-in) |
| Direction 2 | User types `@eerly` inside SAP Joule → routes to Eerly Studio | ✅ Working (via bridge adapter) |

Both directions use the **same contract interface** (`POST /chat`) — meaning swapping in real SAP Joule or real Eerly AI Studio requires only a URL change in `.env`, no code changes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SAP BTP (AI Core)                        │
│  ┌──────────────────┐          ┌──────────────────────────┐ │
│  │  Eerly Studio    │◄────────►│   Joule Persona          │ │
│  │  (port 8000)     │  A2A     │   (port 8001)            │ │
│  │  SAP Expert AI   │  Bridge  │   SAP Joule stand-in     │ │
│  └──────────────────┘          └──────────────────────────┘ │
│           │                              │                   │
│           └──────────┬───────────────────┘                   │
│                      ▼                                       │
│            SAP AI Core GPT-4.1                              │
│            (Generative AI Hub)                              │
└─────────────────────────────────────────────────────────────┘
         ▲
         │ ngrok tunnel (local dev / demo)
         │
    localhost:8000 / 8001
```

### Modular design — swap agents without touching bridge code

```
AGENT_BASE_URL=https://your-eerly-url    # sandbox → real Eerly: change this only
JOULE_BASE_URL=http://localhost:8001     # persona → real Joule: change this only
```

---

## Repository Structure

```
sap-btp-a2a/
├── agent/
│   └── eerly_studio/          # Eerly Studio — SAP Expert proxy agent
│       ├── api.py             # FastAPI REST wrapper — POST /chat on port 8000
│       ├── app.py             # Streamlit UI with @mention routing
│       ├── graph.py           # LangGraph conversational graph
│       ├── a2a_bridge.py      # Agent registry and routing logic
│       ├── sap_llm.py         # SAP AI Core LLM adapter (GPT-4.1)
│       └── requirements.txt
│
├── bridge/                    # A2A contract layer — provider-agnostic
│   ├── adapter.py             # AgentAdapter + JouleAdapter
│   ├── config.py              # Reads all config from .env
│   ├── server.js              # CF Node.js bridge (Joule → Eerly, future)
│   ├── manifest.yml           # CF deployment config
│   └── test_adapter.py        # Isolated adapter tests
│
├── joule_persona/             # SAP Joule stand-in agent
│   ├── api.py                 # FastAPI REST wrapper — POST /chat on port 8001
│   ├── graph.py               # LangGraph graph with Joule persona
│   └── prompts.py             # Joule system prompt (swap file for real Joule)
│
├── tests/
│   ├── test_token_at.py       # SAP AI Core OAuth token test
│   ├── test_completion.py     # SAP AI Core completions test
│   └── test_e2e.py            # Full A2A E2E test suite — 6/6 directions
│
├── ngrok/                     # Local tunnel binary (gitignored)
├── .env.example               # All required environment variables
├── .gitignore
└── README.md                  # This file
```

---

## Prerequisites

### Accounts and services required

| Requirement | Details |
|---|---|
| SAP BTP account | PAYG or enterprise — subaccount with AI Core enabled |
| SAP AI Core | Extended plan (not Standard) — required for orchestration |
| SAP AI Core deployment | GPT-4.1 deployment in Running state |
| Python | 3.11 or 3.12 |
| ngrok | Free account — for local tunnel during demo |

### Tools

```bash
# Verify Python version
python --version   # must be 3.11+

# Verify pip
pip --version

# Verify ngrok
ngrok version      # must be 3.x
```

---

## Quick Start — Sandbox Demo

### Step 1 — Clone the repository

```bash
git clone https://github.com/apoorvaeerly/SAP_BTP.git
cd SAP_BTP/sap-btp-a2a
```

### Step 2 — Create and activate virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Mac/Linux
python -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r agent/eerly_studio/requirements.txt
pip install fastapi uvicorn
```

### Step 4 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in all values. See [Environment Variables](#environment-variables) section below for details on each key.

### Step 5 — Verify SAP AI Core credentials

```bash
python tests/test_token_at.py
# Expected: Status code: 200

python tests/test_completion.py
# Expected: Status code: 200 with a GPT-4.1 response
```

### Step 6 — Start Eerly Studio agent

Open **Window 1** in your terminal:

```bash
uvicorn agent.eerly_studio.api:app --port 8000 --reload
# Expected: Application startup complete.
```

### Step 7 — Start Joule persona agent

Open **Window 2** in your terminal:

```bash
uvicorn joule_persona.api:app --port 8001 --reload
# Expected: Application startup complete.
```

### Step 8 — Start ngrok tunnel

Open **Window 3** in your terminal:

```bash
# Windows
ngrok\ngrok.exe http 8000

# Mac/Linux
ngrok http 8000
```

Copy the `https://` forwarding URL and update your `.env`:

```dotenv
AGENT_BASE_URL=https://your-ngrok-url.ngrok-free.dev
```

### Step 9 — Run validation suite

Open **Window 4** in your terminal:

```bash
# Test both adapters in isolation
python bridge/test_adapter.py

# Run full E2E test — both directions
python tests/test_e2e.py
# Expected: 6/6 tests passed
```

### Step 10 — Launch Streamlit UI (optional)

```bash
streamlit run agent/eerly_studio/app.py
```

Open `http://localhost:8501` in your browser. Type a message to talk to Eerly Studio. Type `@joule <question>` to route to the Joule persona.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values. Never commit `.env` to Git.

```dotenv
# ── SAP AI Core ───────────────────────────────────────────────
AI_CORE_CLIENT_ID=         # From AI Core service key JSON → uaa.clientid
AI_CORE_CLIENT_SECRET=     # From AI Core service key JSON → uaa.clientsecret
AI_CORE_AUTH_URL=          # From AI Core service key JSON → uaa.url + /oauth/token
AI_CORE_API_URL=           # From AI Core service key JSON → serviceurls.AI_API_URL
AI_CORE_RESOURCE_GROUP=default
SAP_MODEL_NAME=gpt-4.1

# ── Eerly Studio agent (sandbox) ──────────────────────────────
AGENT_PROVIDER=sandbox     # sandbox | eerly (real Eerly AI Studio)
AGENT_BASE_URL=            # ngrok URL pointing to port 8000
AGENT_API_KEY=             # Leave empty for sandbox
AGENT_TIMEOUT=60           # Seconds — AI Core can be slow

# ── Joule persona agent ────────────────────────────────────────
JOULE_BASE_URL=http://localhost:8001   # Change to real Joule URL when available
JOULE_API_KEY=             # Leave empty for persona stand-in

# ── Langfuse tracing (optional) ───────────────────────────────
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

### How to get the SAP AI Core service key

1. Go to **SAP BTP Cockpit → Services → Instances and Subscriptions**
2. Click the `>` arrow on your AI Core instance
3. Go to the **Service Keys** tab
4. Download or view the JSON
5. Extract the five fields listed above

---

## SAP BTP Setup — Step by Step

If you are setting up a new SAP BTP account from scratch, follow these steps in order.

### 1. Create a subaccount

- Go to your Global Account in BTP Cockpit
- Click **Create Subaccount**
- Choose a region (e.g. `us10` — US East AWS)
- Enable Cloud Foundry during creation

### 2. Provision SAP AI Core — Extended plan

- Go to **Services → Service Marketplace**
- Search for **SAP AI Core**
- Select plan: **Extended** (not Standard — Standard lacks orchestration)
- Create an instance
- Go to the instance → **Service Keys** → Create a service key
- Download the JSON — this contains all credentials

### 3. Verify AI Core is working

```bash
python tests/test_token_at.py     # confirms OAuth works
python tests/test_completion.py   # confirms GPT-4.1 responds
```

### 4. Create a Cloud Foundry space

- Go to **Cloud Foundry → Spaces**
- Click **Create Space**
- Name it `eerly-bridge` or similar
- Note the CF API endpoint from the subaccount Overview page

### 5. Confirm deployments are running

- Open **SAP AI Launchpad** (subscribed from Instances and Subscriptions)
- Go to **ML Operations → Deployments**
- Confirm at least one deployment is in **Running** status
- Note the deployment ID — used in `test_completion.py`

---

## A2A Contract Interface

Every agent in this system — sandbox or real — must implement this contract:

### Request

```http
POST /chat
Content-Type: application/json

{
  "message": "Your question here"
}
```

### Response

```json
{
  "reply": "The agent's answer",
  "agent_used": "studio | joule",
  "status": "ok",
  "note": "Optional metadata"
}
```

### Health check

```http
GET /health

Response: { "status": "ok", "service": "agent-name" }
```

This contract is defined in `bridge/adapter.py`. The response field normalisation chain handles variations:

```python
reply = data.get("reply") or data.get("response") or data.get("text") or data.get("output")
```

---

## Plugging In Real Eerly AI Studio

When Accely provides the Eerly AI Studio API credentials:

**Step 1** — Get from Accely:
- Base URL (e.g. `https://api.eerly.ai`)
- Auth header format (`Bearer` token or `X-API-Key`)
- Chat endpoint path (e.g. `/api/v1/chat`)
- Request field name (`message`, `query`, or `prompt`)
- Response field name (`reply`, `response`, or `text`)

**Step 2** — Update `.env`:

```dotenv
AGENT_PROVIDER=eerly
AGENT_BASE_URL=https://api.eerly.ai
AGENT_API_KEY=your-eerly-api-key
```

**Step 3** — If Eerly's response field name differs, update the normalisation chain in `bridge/adapter.py` line ~35.

**Step 4** — Verify:

```bash
python bridge/test_adapter.py
python tests/test_e2e.py
```

No other code changes required anywhere.

---

## Plugging In Real SAP Joule

### Option A — SuccessFactors Joule (fastest path)

1. Confirm your SF Joule instance supports HTTP skill extensibility (ask SF admin)
2. Deploy the CF bridge app (see `bridge/README.md`)
3. Register the bridge app URL as an HTTP skill in SF Joule admin
4. Update `.env`:

```dotenv
JOULE_BASE_URL=https://your-cf-bridge-app.cfapps.us10.hana.ondemand.com
JOULE_API_KEY=your-joule-credentials
```

### Option B — SAP Build Work Zone

1. Subscribe to SAP Build Work Zone in your BTP subaccount
2. Register `@Eerly` as an HTTP Action skill in SAP Build
3. Point the skill at the CF bridge app `/ask` endpoint
4. The bridge app forwards to Eerly Studio automatically

### Option C — S/4HANA Joule (full production)

- Requires SAP commercial agreement and 20+ day implementation
- IAS trust configuration between BTP and S/4HANA tenant required
- Skill registration via SAP Build Process Automation
- See `docs/joule_enablement.md` for full step-by-step guide

### Swapping the Joule stand-in for real Joule

In `joule_persona/api.py`, replace the `graph.invoke()` call with:

```python
response = requests.post(
    f"{JOULE_BASE_URL}/chat",
    json={"message": req.message},
    headers={"Authorization": f"Bearer {JOULE_API_KEY}"},
    timeout=30
)
return ChatResponse(reply=response.json().get("reply", ""))
```

---

## Running Tests

```bash
# Test OAuth token only
python tests/test_token_at.py

# Test AI Core completions
python tests/test_completion.py

# Test both bridge adapters in isolation
python bridge/test_adapter.py

# Full E2E — both A2A directions
python tests/test_e2e.py
```

### Expected E2E output

```
Direction 1 — Eerly Studio : 3/3 passed
Direction 2 — Joule persona: 3/3 passed
Total                      : 6/6 passed
All tests passed.
Both A2A directions are operational and ready for demo.
```

---

## Demo Script

### Setup before the demo

1. Start Eerly Studio: `uvicorn agent.eerly_studio.api:app --port 8000 --reload`
2. Start Joule persona: `uvicorn joule_persona.api:app --port 8001 --reload`
3. Start ngrok: `ngrok\ngrok.exe http 8000`
4. Update `AGENT_BASE_URL` in `.env` with new ngrok URL
5. Run `python tests/test_e2e.py` — confirm 6/6 passing
6. Start Streamlit: `streamlit run agent/eerly_studio/app.py`

### Scenario 1 — Eerly Studio answers an SAP question

> Open Streamlit at `http://localhost:8501`
> Type: `What is SAP BTP and how does AI Core fit into it?`
> Show: Eerly Studio responds with structured SAP knowledge

**Talking point:** Eerly AI Studio is built natively on SAP BTP, using SAP AI Core as its LLM backend. It answers SAP questions with enterprise-grade accuracy.

### Scenario 2 — @joule routing from Eerly Studio

> In the same Streamlit window
> Type: `@joule What are the key modules of SAP S/4HANA?`
> Show: Request routes to the Joule agent, response comes back with Joule's branding

**Talking point:** This is A2A in action. Eerly Studio detects the `@joule` mention, routes the query through the A2A bridge to the Joule agent, and surfaces the response inline — without the user leaving Eerly Studio.

### Scenario 3 — Out-of-scope rejection

> Type: `Who won the FIFA World Cup in 2022?`
> Show: Eerly rejects with SAP-only message
> Type: `@joule What is the weather today?`
> Show: Joule rejects with its own persona message

**Talking point:** Both agents are domain-restricted. Eerly only answers SAP questions. Joule only answers SAP ecosystem questions. The guardrails are enforced at the system prompt level — independent of the bridge layer.

---

## Troubleshooting

### OAuth token fails — `invalid_login_request`

**Cause:** Special characters (especially `!`) in client ID or secret being corrupted by Windows CMD.
**Fix:** Use PowerShell or a Python script instead of curl. The `test_token_at.py` script handles this correctly.

### AI Core returns 404

**Cause:** Wrong deployment ID or missing `api-version` query parameter.
**Fix:** Add `?api-version=2024-02-01` to the endpoint URL. Confirm deployment is in Running state in AI Launchpad.

### ngrok returns 404 HTML

**Cause:** ngrok browser warning page being served instead of the actual response.
**Fix:** Always include the header `ngrok-skip-browser-warning: true` in requests. The bridge adapter adds this automatically when the URL contains `ngrok`.

### ngrok URL changed

**Cause:** ngrok free plan generates a new URL on every restart.
**Fix:** After restarting ngrok, update `AGENT_BASE_URL` in `.env` and restart uvicorn. On the free plan this is expected — upgrade to ngrok paid plan for a static URL.

### Eerly request times out

**Cause:** SAP AI Core GPT-4.1 can take 20–40 seconds on cold responses.
**Fix:** Set `AGENT_TIMEOUT=60` in `.env`. The default is 30s which is too short for AI Core.

### `ModuleNotFoundError` on import

**Cause:** Running scripts from the wrong directory.
**Fix:** Always run commands from the project root `D:\SAP_BTP\sap-btp-a2a\`, not from inside subfolders.

---

## Roadmap

| Item | Status |
|---|---|
| Eerly Studio sandbox agent | ✅ Done |
| Joule persona stand-in | ✅ Done |
| Bridge adapter layer | ✅ Done |
| E2E test suite 6/6 | ✅ Done |
| Main README | ✅ Done |
| Sub-folder READMEs | 🔲 In progress |
| CF bridge app deployment | 🔲 Pending |
| SF Joule HTTP skill registration | 🔲 Pending SF admin |
| Real Eerly AI Studio integration | 🔲 Pending Accely API docs |
| S/4HANA Joule integration | 🔲 Pending commercial agreement |
| Demo screen recordings | 🔲 Pending |

---

## Contributing

This repository is maintained by the Accely Solutions DMCC team. For questions about the SAP BTP setup, contact the team via the internal project channel.

When adding a new agent provider:

1. Add config class to `bridge/config.py`
2. Add adapter class to `bridge/adapter.py` — implement `.chat(message)` method
3. Add test cases to `tests/test_e2e.py`
4. Update `.env.example` with new variables
5. Document the swap steps in this README under the relevant "Plugging In" section