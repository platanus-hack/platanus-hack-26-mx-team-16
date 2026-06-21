# Planted demo bot (03-agentic-surface §3.5)

A minimal, guardrail-free chatbot with a **CANARY secret** in its system prompt.
It is the target for the demo's *star finding*: a 100%-reproducible canary leak
that needs no third party and no model API key.

## Run it

```bash
cd backend
uv run uvicorn demo.planted_bot.app:app --host 127.0.0.1 --port 8400
# optional: override the planted secret
PLANTED_BOT_CANARY="DEMO-CANARY-XYZ" uv run uvicorn demo.planted_bot.app:app --port 8400
```

## Point a scan at it

```bash
export PLANTED_BOT_URL="http://localhost:8400"
# localhost is allow-listed for the agentic bridge via the default demo hosts in
# src/scans/worker/agentic/probe.py (assert_public_target rejects loopback otherwise).
# Add more hosts with AGENTIC_ALLOWED_DEMO_HOSTS="host1,host2".
```

## Why it leaks

`GET /` exposes a detectable generic chat surface (an "ask me" `<textarea>` +
`window.OwliverDemoChat`), so the detector reports a surface. The `canary-*`
payload substitutes `{{CANARY}}` with a unique runtime token; `POST /chat`
obediently echoes any control token, so the token appears in the reply. The
**regex** judge (`judge.py`, no LLM) flags a high-confidence `LLM01` leak with
`evidence={payload, respuesta_cruda, veredicto, reason, token_filtrado}`.

This is a **demo fixture**, not product code — it lives outside `src/` and is
never imported by the app or the worker.

### Decision left open (plan §11.8)

Whether to keep this bot as a permanent versioned fixture or stand it up ad-hoc
for the demo is intentionally not decided here — both work. It is currently
versioned so the smoke test (`test_planted_bot_e2e`, gated) can target it.
