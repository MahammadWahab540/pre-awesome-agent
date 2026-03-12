---
name: qa-e2e-regression
description: Run high-signal regression checks across frontend, backend, and conversation stages for the voice agent. Use when validating fixes, preparing releases, or debugging cross-layer failures affecting stage flow, transcripts, audio, or deployment readiness.
---

# QA E2E Regression

Use a compact but strict regression pass focused on user-critical path.

## Use This Workflow

1. Validate backend boot and API contracts.
- Start backend service and verify:
  - `GET /health`
  - `GET /config/stages`
  - `/ws` setup handshake and `session_confirmed`

2. Validate frontend boot and session flow.
- Start frontend and verify:
  - home form validation
  - start session navigation with expected query params
  - resume session path from local storage

3. Validate conversation-stage behavior.
- Confirm stage index starts at 0 for a new session.
- Confirm stage progression updates UI tracker.
- Confirm transcript panel receives both user and model text.
- Confirm payment path branching behavior (EMI vs full payment/credit card).

4. Validate release safety.
- Run frontend build (`npm run build`).
- Confirm no instruction-to-config mismatch in stage files.
- Confirm deployment script still matches environment expectations.

## Defect Reporting Format

- Environment: local or deployed target
- Layer: frontend, backend, prompt, deploy
- Repro steps: minimal numbered steps
- Expected vs actual
- Blocking impact: yes or no
- Suspected file(s)
