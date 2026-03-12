---
name: frontend-voice-session
description: Build, debug, and extend the Next.js frontend for the NxtWave voice registration flow. Use when tasks involve `frontend/app/page.tsx`, `frontend/app/session/page.tsx`, live WebSocket audio UX, transcript/stage rendering, session resume behavior, or frontend build/runtime issues.
---

# Frontend Voice Session

Keep the frontend aligned to the business flow: capture user details, start or resume a session, connect to backend WebSocket, and reflect conversation progress clearly.

## Use This Workflow

1. Inspect the entry and routing flow first.
- `frontend/app/page.tsx`
- `frontend/app/session/page.tsx`
- `frontend/lib/multimodal-live/session-store.ts`

2. Inspect live connection and media pipeline next.
- `frontend/multimodal-live/MultimodalLiveApp.tsx`
- `frontend/hooks/multimodal-live/use-live-api.ts`
- `frontend/utils/multimodal-live/*`

3. Preserve these invariants during edits.
- Keep `mobile_number` and `session_id` as required query params for `/session`.
- Keep `user_name` and `user_language` passed into `connect(...)`.
- Keep handshake states consistent: `wsReady` -> user click -> `connect` -> `sessionconfirmed`.
- Keep transcript updates wired to ADK events (`input_transcription`, `output_transcription`).
- Keep stage updates wired to `actions.state_delta.current_stage_index`.

4. Validate before finishing.
- Run `npm run build` in `frontend`.
- If runtime issue is reported, run `npm run dev` and reproduce with a valid session URL.

## Common Fix Targets

- Session launch broken: verify query param naming (`mobile_number`, `session_id`, `name`, `lang`).
- No "Start Session" enablement: verify mobile length and name checks in `app/page.tsx`.
- No transcript updates: verify `on("adkevent")` and content handlers in `MultimodalLiveApp.tsx`.
- Audio/turn-state issues: verify event handling in `use-live-api.ts` (`interrupted`, `turncomplete`, `audio`, transcriptions).
