# Root Agent Description

The Root Agent is the main orchestrator for the BRD creation process. It manages the sequential flow through 7 specialized stages, ensuring that each sub-agent completes its work before moving to the next stage.

## Responsibilities

- Route conversations to the appropriate sub-agent based on current stage
- Maintain conversation context across stage transitions
- Detect stage completion signals from sub-agents
- Manage state through the external StateManager
- Ensure strict sequential progression through the BRD stages

## Architecture

The Root Agent uses a SequentialAgent pattern where:
- Each sub-agent is a specialist for one stage of the BRD
- Sub-agents output state updates that signal completion
- The Root Agent coordinates handoffs between sub-agents
- State is persisted externally in Firebase for session continuity
