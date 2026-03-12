---
name: backend-stage-orchestrator
description: Build and maintain the FastAPI plus Google ADK backend that drives staged voice conversations. Use when tasks involve session setup, WebSocket flow, agent orchestration, stage callbacks/tools, state transitions, language handling, or backend reliability issues.
---

# Backend Stage Orchestrator

Keep backend behavior aligned to the business objective: reliably move each learner through qualification and payment-path decisions with explicit state control.

## Use This Workflow

1. Start from orchestration and runtime entrypoints.
- `my-awesome-agent/app/fast_api_app.py`
- `my-awesome-agent/app/agent.py`
- `my-awesome-agent/app/agents/consultant.py`

2. Review stage/state coupling before changing logic.
- `my-awesome-agent/app/config/stages_config.json`
- `my-awesome-agent/app/callbacks/stage_management.py`
- `my-awesome-agent/app/agents/tools.py`
- `my-awesome-agent/app/instructions/*.md`

3. Preserve these invariants.
- Require setup payload with valid `user_id` and `session_id` before running agent session.
- Keep `current_stage_index` and `payment_path` present in session state.
- Do not break stage tool wiring (`tool_name` in config must exist in `TOOLS_MAP`).
- Keep session resume protection logic (`is_resuming` guard and replay protection).
- Keep language/voice mapping stable unless a deliberate product change is requested.

4. Validate backend changes.
- Run service locally: `uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000` from `my-awesome-agent`.
- Confirm `GET /health` and `GET /config/stages` respond.
- Confirm `/ws` accepts setup and emits `session_confirmed`.

## Common Fix Targets

- Stage not progressing: verify tool call name and callback handling.
- Repeated greetings after reconnect: verify `current_stage_index` persistence and `is_resuming` clearing logic.
- Wrong language/voice: verify `user_language` capture in setup and mapping functions.
- Missing frontend stage updates: verify `manager.send_stage_update(...)` trigger path.
