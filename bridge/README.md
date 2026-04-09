# Bridge — A2A Contract Layer

This module is the **provider-agnostic contract layer** between SAP Joule and Eerly AI Studio. It defines the A2A interface contract, implements adapters for each agent provider, and contains the CF Node.js bridge app for the Joule → Eerly direction in production.

---

## What This Module Does

- Defines the A2A contract: `POST /chat` with `{ "message" }` → `{ "reply" }`
- Implements `AgentAdapter` — calls Eerly Studio (sandbox or real)
- Implements `JouleAdapter` — calls Joule persona (stand-in or real Joule)
- Provides `server.js` — a Node.js Express app for CF deployment (Joule → Eerly direction)
- Centralises all configuration via `config.py` reading from `.env`

---

## File Reference

| File | Purpose |
|---|---|
| `adapter.py` | `AgentAdapter` + `JouleAdapter` — the contract implementation |
| `config.py` | `AgentConfig` + `JouleConfig` — reads all settings from `.env` |
| `server.js` | CF Node.js bridge — receives Joule HTTP skill call, forwards to Eerly |
| `manifest.yml` | SAP BTP Cloud Foundry deployment manifest |
| `package.json` | Node.js dependencies for `server.js` |
| `test_adapter.py` | Isolated adapter tests — run before E2E tests |
| `__init__.py` | Makes this a Python package |

---

## The A2A Contract

Every agent in this system must implement this exact interface:

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
  "reply": "The agent's answer as plain text or markdown",
  "agent_used": "studio | joule",
  "status": "ok",
  "note": "Optional metadata about the response"
}
```

### Health check

```http
GET /health

Response: { "status": "ok", "service": "agent-name" }
```

### Response field normalisation

Different agents may use different field names for the reply. The adapter handles this automatically:

```python
reply = (
    data.get("reply")      # Eerly Studio, Joule persona
    or data.get("response")
    or data.get("text")
    or data.get("answer")
    or data.get("output")
    or str(data)           # fallback — surfaces raw JSON for debugging
)
```

---

## Python Adapters

### AgentAdapter — Eerly Studio

Controls the Eerly Studio direction. Switch providers via `AGENT_PROVIDER` in `.env`:

| `AGENT_PROVIDER` | What it calls |
|---|---|
| `sandbox` | Local LangGraph agent at `AGENT_BASE_URL` (current) |
| `eerly` | Real Eerly AI Studio API at `AGENT_BASE_URL` (future) |

```python
from bridge.adapter import AgentAdapter

adapter = AgentAdapter()
reply = adapter.chat("What is SAP BTP?")
```

### JouleAdapter — SAP Joule

Controls the Joule direction. Switch by updating `JOULE_BASE_URL` in `.env`:

| `JOULE_BASE_URL` | What it calls |
|---|---|
| `http://localhost:8001` | Local Joule persona stand-in (current) |
| `https://your-cf-bridge.cfapps...` | CF bridge → real Joule (future) |

```python
from bridge.adapter import JouleAdapter

adapter = JouleAdapter()
reply = adapter.chat("What is SAP S/4HANA?")
```

### Running the adapter test

```bash
# From project root
python bridge/test_adapter.py
```

Expected output:

```
Testing: Eerly Studio (AgentAdapter)
Q: What is SAP BTP?
A: SAP BTP (Business Technology Platform) is...

Testing: SAP Joule persona (JouleAdapter)
Q: What is SAP S/4HANA?
A: SAP S/4HANA is SAP's next-generation ERP...
```

---

## Configuration

All configuration is read from `.env` at project root via `config.py`.

### AgentConfig

| Variable | Default | Description |
|---|---|---|
| `AGENT_PROVIDER` | `sandbox` | Provider switch: `sandbox` or `eerly` |
| `AGENT_BASE_URL` | None | ngrok URL (sandbox) or real Eerly URL (production) |
| `AGENT_API_KEY` | `""` | Empty for sandbox, Eerly API key for production |
| `AGENT_TIMEOUT` | `30` | Request timeout in seconds — set to `60` for AI Core |

### JouleConfig

| Variable | Default | Description |
|---|---|---|
| `JOULE_BASE_URL` | `http://localhost:8001` | Joule persona (local) or real Joule endpoint |
| `JOULE_API_KEY` | `""` | Empty for persona, Joule credentials for production |

---

## CF Node.js Bridge App (server.js)

The `server.js` file is the **production bridge** for the Joule → Eerly direction. It is deployed to SAP BTP Cloud Foundry and acts as the target URL for SAP Joule's HTTP Action skill.

### How it works

```
SAP Joule (HTTP skill)
        │
        │  POST /ask  { "query": "..." }
        ▼
  server.js on CF
        │
        │  POST /chat  { "message": "..." }
        ▼
  Eerly AI Studio API
        │
        │  { "reply": "..." }
        ▼
  server.js (maps response)
        │
        │  { "response": "..." }
        ▼
SAP Joule (displays answer)
```

### Placeholders to confirm before deploying

Before deploying `server.js`, confirm these with Accely:

| Placeholder | Location | What to confirm |
|---|---|---|
| `/api/v1/chat` | Line ~71 | Actual Eerly chat endpoint path |
| `message:` | Line ~63 | Request field name (`message`, `query`, or `prompt`) |
| `reply` | Line ~76 | Response field name (`reply`, `response`, or `text`) |
| `Bearer` | Line ~57 | Auth scheme (`Bearer` token or `X-API-Key`) |

---

## CF Deployment — Step by Step

Follow these steps when you are ready to deploy the bridge app to SAP BTP Cloud Foundry. This enables the `@Eerly` direction inside a real SAP Joule UI.

### Prerequisites

- CF CLI v8 installed
- SAP BTP CF space created (e.g. `eerly-bridge`)
- CF API endpoint noted (e.g. `https://api.cf.us10-001.hana.ondemand.com`)
- Eerly AI Studio API credentials from Accely (URL, key, field names)

### Step 1 — Install CF CLI

Download from: https://github.com/cloudfoundry/cli/releases

Verify:

```bash
cf version   # must be v8+
```

### Step 2 — Log in to SAP BTP CF

```bash
cf login -a https://api.cf.us10-001.hana.ondemand.com
# Enter your SAP BTP email and password when prompted
```

### Step 3 — Target your org and space

```bash
cf target -o "Accely Solutions DMCC" -s "eerly-bridge"
```

### Step 4 — Update server.js placeholders

Open `bridge/server.js` and replace:
- `/api/v1/chat` with the actual Eerly endpoint path
- `message:` with the actual request field name
- `.reply` with the actual response field name

### Step 5 — Install Node.js dependencies locally (optional)

```bash
cd bridge
npm install
cd ..
```

### Step 6 — Set environment variables (never put secrets in manifest.yml)

```bash
cf set-env eerly-bridge EERLY_API_URL "https://api.eerly.ai"
cf set-env eerly-bridge EERLY_API_KEY "your-eerly-api-key-here"
```

### Step 7 — Deploy

```bash
cf push
# Reads manifest.yml automatically
# CF buildpack installs Node.js dependencies
```

### Step 8 — Note your public URL

```bash
cf app eerly-bridge
# Look for: routes: eerly-bridge-xxxx.cfapps.us10.hana.ondemand.com
```

This URL is what you register as the Joule HTTP skill endpoint.

### Step 9 — Smoke test

```bash
curl -X POST https://your-cf-route.cfapps.us10.hana.ondemand.com/ask \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"What is SAP BTP?\"}"
```

Expected:

```json
{ "response": "SAP BTP (Business Technology Platform) is..." }
```

### Step 10 — Tail logs

```bash
cf logs eerly-bridge --recent    # last N lines
cf logs eerly-bridge             # live tail during demo
```

### Updating after changes

```bash
cf push                          # redeploy
cf set-env eerly-bridge KEY val  # update env var
cf restage eerly-bridge          # apply env var change without redeploy
```

---

## Registering @Eerly as a Joule Skill

Once the CF bridge app is deployed, register it as a skill in SAP Joule.

### Via SAP Build Process Automation (PAYG accounts)

1. Go to **SAP Build Process Automation** in your BTP subaccount
2. Navigate to **Skills → Create Skill → HTTP Action**
3. Configure:
   - **Name:** `Eerly AI Studio`
   - **Handle:** `@eerly`
   - **URL:** `https://your-cf-route.cfapps.us10.hana.ondemand.com/ask`
   - **Method:** `POST`
   - **Request body:** `{ "query": "{{user_input}}" }`
   - **Response field:** `response`
4. Save and publish the skill

### Via SuccessFactors Joule Admin

1. Go to SF Admin Center → Joule Configuration
2. Navigate to **Skills → Register External Skill**
3. Provide the CF bridge app URL and authentication details
4. Map `{{user_input}}` to the `query` field in the request body
5. Map the `response` field from the bridge app response

---

## Adding a New Agent Provider

To add a third agent (e.g. a different AI assistant):

**Step 1 — Add config to `config.py`:**

```python
class NewAgentConfig:
    BASE_URL        = os.getenv("NEW_AGENT_BASE_URL")
    API_KEY         = os.getenv("NEW_AGENT_API_KEY", "")
    REQUEST_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
```

**Step 2 — Add adapter to `adapter.py`:**

```python
from bridge.config import NewAgentConfig

class NewAgentAdapter:
    def __init__(self):
        self.base_url = NewAgentConfig.BASE_URL
        self.api_key  = NewAgentConfig.API_KEY
        self.timeout  = NewAgentConfig.REQUEST_TIMEOUT

    def chat(self, message: str) -> str:
        return _call_agent(
            base_url=self.base_url,
            api_key=self.api_key,
            message=message,
            timeout=self.timeout,
            provider_name="new_agent"
        )
```

**Step 3 — Add test cases to `test_adapter.py` and `tests/test_e2e.py`.**

**Step 4 — Add `NEW_AGENT_BASE_URL` and `NEW_AGENT_API_KEY` to `.env.example`.**

---

## Troubleshooting

### Adapter returns `[sandbox] HTTP 404: <!DOCTYPE html>`

ngrok is returning its browser warning page. The `ngrok-skip-browser-warning` header is added automatically when the URL contains `ngrok`. Check that `AGENT_BASE_URL` in `.env` contains the word `ngrok` in the domain.

### Adapter returns `[sandbox] Request timed out after 30s`

SAP AI Core can take 20–40 seconds on complex queries. Set `AGENT_TIMEOUT=60` in `.env`.

### CF push fails with memory error

Your CF space quota may be exhausted. Check with:

```bash
cf space eerly-bridge
```

The bridge app needs 256MB. Increase quota in BTP cockpit if needed.

### CF app starts but returns 502 on /ask

`EERLY_API_URL` or `EERLY_API_KEY` env var is missing or wrong. Check with:

```bash
cf env eerly-bridge
```

Then update and restage:

```bash
cf set-env eerly-bridge EERLY_API_URL "https://correct-url"
cf restage eerly-bridge
```