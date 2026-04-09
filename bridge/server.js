/**
 * @Eerly Bridge App
 * Deployed to SAP BTP Cloud Foundry.
 * Receives HTTP POST from SAP Joule skill, forwards to Eerly AI Studio API,
 * returns response inline to Joule.
 *
 * ⚠️  PLACEHOLDERS — confirm against Eerly API docs from Accely:
 *   - EERLY_CHAT_PATH      (line ~60)  e.g. /api/v1/chat  or  /v1/messages
 *   - request body shape   (line ~63)  key name: "message" | "query" | "prompt"
 *   - response field       (line ~72)  key name: "reply"  | "response" | "text"
 *   - auth scheme          (line ~57)  Bearer token vs API-Key header
 */

'use strict';

const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

// ── Health check (CF router + Joule skill validation) ─────────────────────────
app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'eerly-bridge' }));

// ── Main skill endpoint ───────────────────────────────────────────────────────
/**
 * Joule HTTP Action skill POSTs:
 * {
 *   "query": "<user's @Eerly question>",
 *   "context": { "userId": "...", "sessionId": "..." }   // optional, Joule may send this
 * }
 *
 * We respond with:
 * {
 *   "response": "<Eerly's answer as plain text>"
 * }
 */
app.post('/ask', async (req, res) => {
    const { query, context } = req.body;

    // Basic input guard
    if (!query || typeof query !== 'string' || query.trim() === '') {
        return res.status(400).json({ response: 'No query provided.' });
    }

    // ── Build Eerly request ─────────────────────────────────────────────────────
    const eerlyUrl = process.env.EERLY_API_URL; // e.g. https://api.eerly.ai

    if (!eerlyUrl) {
        console.error('EERLY_API_URL env var is not set');
        return res.status(500).json({ response: 'Bridge misconfigured: missing EERLY_API_URL.' });
    }

    const requestBody = {
        // ⚠️  CONFIRM field name with Accely ("message", "query", or "prompt")
        message: query.trim(),

        // Pass through session context if Eerly supports it — remove if not needed
        ...(context?.sessionId && { session_id: context.sessionId }),
    };

    const headers = {
        'Content-Type': 'application/json',
        // ⚠️  CONFIRM auth scheme — most likely Bearer; could be "X-API-Key" or "ApiKey"
        'Authorization': `Bearer ${process.env.EERLY_API_KEY}`,
    };

    // ── Call Eerly ──────────────────────────────────────────────────────────────
    try {
        const eerlyRes = await axios.post(
            // ⚠️  CONFIRM path — e.g. /api/v1/chat  /v1/conversations  /chat/completions
            `${eerlyUrl}/api/v1/chat`,
            requestBody,
            { headers, timeout: 25000 }   // 25 s — covers Eerly + any upstream LLM latency
        );

        // ⚠️  CONFIRM response field — common candidates: .reply  .response  .text  .answer
        const answer = eerlyRes.data?.reply
            ?? eerlyRes.data?.response
            ?? eerlyRes.data?.text
            ?? eerlyRes.data?.answer
            ?? JSON.stringify(eerlyRes.data); // fallback: surface raw JSON so you can see the shape

        return res.json({ response: answer });

    } catch (err) {
        // Surface enough detail to debug during the demo without leaking secrets
        const status = err.response?.status;
        const detail = err.response?.data
            ? JSON.stringify(err.response.data).slice(0, 300)
            : err.message;

        console.error(`Eerly API error [${status}]:`, detail);

        const userMsg = status === 401
            ? 'Eerly authentication failed — check EERLY_API_KEY.'
            : status === 404
                ? 'Eerly endpoint not found — check EERLY_API_URL / path.'
                : `Eerly returned an error (${status ?? 'network'}): ${detail}`;

        return res.status(502).json({ response: userMsg });
    }
});

// ── Start ─────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;   // CF injects PORT automatically
app.listen(PORT, () => console.log(`eerly-bridge listening on port ${PORT}`));
