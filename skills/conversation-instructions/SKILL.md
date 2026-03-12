---
name: conversation-instructions
description: Edit and maintain stage instruction prompts that control PRE call behavior and business policy. Use when tasks involve `app/instructions/*.md`, payment-path rules, discounts, confirmation gates, stage completion criteria, or session output contract changes.
---

# Conversation Instructions

Treat instruction files as policy and behavior contracts, not generic copy.

## Use This Workflow

1. Load all coupled files before editing.
- `my-awesome-agent/app/instructions/Qualification.md`
- `my-awesome-agent/app/instructions/EMI Onboarding & Completion.md`
- `my-awesome-agent/app/config/stages_config.json`
- `my-awesome-agent/app/agents/tools.py`

2. Preserve business-critical behavior.
- Keep turn order explicit and checkpoint driven.
- Keep explicit confirmation gates before stage completion.
- Keep payment path routing deterministic (`emi`, `full_payment`, `credit_card`).
- Keep tool call semantics unchanged (`complete_program_explanation`, `complete_payment_structure`).
- Keep constraints that block unauthorized claims or sensitive data collection.

3. Apply repo-specific policy updates consistently.
- If a new business rule is added (for example program-wise discount), reflect it in:
  - turn logic
  - routing guidance
  - stage completion conditions
  - output/session state contract

4. Validate prompt change quality.
- Check for contradictions across turns.
- Check that every new state key is represented in output contract.
- Check that stage IDs, tool names, and config references still align.

## Guardrails

- Do not add ambiguous progression language that can skip explicit consent.
- Do not introduce unsupported product promises.
- Do not change stage IDs or tool names without updating config and code.
