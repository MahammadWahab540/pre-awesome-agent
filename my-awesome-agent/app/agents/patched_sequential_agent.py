"""SequentialAgent wrapper with stable live-mode tool registration."""

from __future__ import annotations

import inspect
import logging
from typing import Any
from typing import AsyncGenerator
from typing import Callable
from typing import Dict
from typing import Optional

from pydantic import PrivateAttr
from typing_extensions import override

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events.event import Event
from google.adk.tools import ToolContext
from google.adk.utils.context_utils import Aclosing

logger = logging.getLogger(__name__)

_TASK_COMPLETED_TOOL_NAME = "task_completed"
_TASK_COMPLETED_INSTRUCTION_MARKER = "call the task_completed function"
_TASK_COMPLETED_INSTRUCTION = (
    "If you finished the user's request according to its description, call the "
    "task_completed function to exit so the next agents can take over. When "
    "calling this function, do not generate any text other than the function "
    "call."
)
_INSTRUCTION_PATCH_FLAG = "_adk_task_completed_instruction_patched"


def _tool_name(tool: Any) -> str:
    """Best-effort name extraction for both callables and BaseTool objects."""
    name = getattr(tool, "name", None)
    if isinstance(name, str) and name:
        return name

    callable_name = getattr(tool, "__name__", None)
    if isinstance(callable_name, str) and callable_name:
        return callable_name

    return ""


def _dedupe_tools_by_name(tools: list[Any]) -> list[Any]:
    """Deduplicates tools by declared name while preserving order."""
    deduped: list[Any] = []
    seen_names: set[str] = set()

    for tool in tools:
        name = _tool_name(tool)
        if name and name in seen_names:
            continue
        if name:
            seen_names.add(name)
        deduped.append(tool)

    return deduped


def _ensure_task_completed_instruction(
    instruction: str | Callable[..., Any]
) -> str | Callable[..., Any]:
    """Appends live exit guidance exactly once."""
    if callable(instruction):
        if getattr(instruction, _INSTRUCTION_PATCH_FLAG, False):
            return instruction

        async def wrapped_instruction(ctx, orig=instruction):
            rendered = orig(ctx)
            if inspect.isawaitable(rendered):
                rendered = await rendered

            text = str(rendered or "")
            if _TASK_COMPLETED_INSTRUCTION_MARKER in text:
                return text
            return f"{text}\n\n{_TASK_COMPLETED_INSTRUCTION}".strip()

        setattr(wrapped_instruction, _INSTRUCTION_PATCH_FLAG, True)
        return wrapped_instruction

    text = str(instruction or "")
    if _TASK_COMPLETED_INSTRUCTION_MARKER in text:
        return text
    return f"{text}\n\n{_TASK_COMPLETED_INSTRUCTION}".strip()


class PatchedSequentialAgent(SequentialAgent):
    """SequentialAgent with deterministic task_completed tool handling.

    stage_guards: optional per-stage entry conditions, keyed by stage index.
    Example: {1: {"requires_payment_path": "emi"}}
    When a guard fails, the stage is skipped and the sequence ends.

    Stored as a PrivateAttr so it is never included in the Pydantic schema
    or serialized to JSON (which cannot handle integer dict keys).
    """

    # Private — not part of the Pydantic model schema, never serialized.
    _stage_guards: Dict[int, Dict[str, Any]] = PrivateAttr(default_factory=dict)
    _enable_task_completed_tool: bool = PrivateAttr(default=True)

    def __init__(
        self,
        stage_guards: Optional[Dict[int, Dict[str, Any]]] = None,
        enable_task_completed_tool: bool = True,
        **data: Any,
    ) -> None:
        # stage_guards is captured here explicitly so it never reaches **data
        # and never confuses Pydantic's field validation.
        super().__init__(**data)
        self._stage_guards = stage_guards or {}
        self._enable_task_completed_tool = enable_task_completed_tool
        if self._enable_task_completed_tool:
            self._patch_llm_sub_agents()

    def _patch_llm_sub_agents(self) -> None:
        for sub_agent in self.sub_agents:
            if not isinstance(sub_agent, LlmAgent):
                continue

            def task_completed(tool_context: ToolContext):
                """
                Signals that the agent has successfully completed the user's
                question or task.
                """
                if tool_context.state.get("is_resuming"):
                    return (
                        "IGNORING completion signal because we are in "
                        "resumption mode. Please speak to the user first."
                    )
                tool_context.state["_should_terminate_agent"] = True
                return "Task completion signaled."

            # Build a clean per-agent tools list once at construction time.
            original_tools = list(getattr(sub_agent, "tools", []) or [])
            tools_without_task_completed = [
                tool
                for tool in original_tools
                if _tool_name(tool) != _TASK_COMPLETED_TOOL_NAME
            ]
            tools_without_task_completed.append(task_completed)
            sub_agent.tools = _dedupe_tools_by_name(tools_without_task_completed)
            sub_agent.instruction = _ensure_task_completed_instruction(
                sub_agent.instruction
            )

    @override
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

        for i, sub_agent in enumerate(self.sub_agents):
            # Check current stage index vs sub-agent index
            # This allows skipping agents if a tool advanced the stage beyond the next one
            current_stage_index = 0
            if hasattr(ctx, "session") and hasattr(ctx.session, "state"):
                current_stage_index = ctx.session.state.get("current_stage_index", 0)
            else:
                logger.warning(f"⚠️ ctx.session or ctx.session.state missing in _run_live_impl! Defaulting current_stage_index to 0.")

            if i < current_stage_index:
                logger.info(f"⏭️ Skipping {sub_agent.name} (index {i}) because current index is {current_stage_index}")
                continue

            # Code-level stage guard: check entry conditions (e.g. payment_path)
            guard = self._stage_guards.get(i, {})
            required_payment_path = guard.get("requires_payment_path")
            if required_payment_path:
                actual_payment_path = ""
                if hasattr(ctx, "session") and hasattr(ctx.session, "state"):
                    actual_payment_path = ctx.session.state.get("payment_path", "")
                if actual_payment_path != required_payment_path:
                    logger.warning(
                        f"🚫 Stage guard blocked stage {i} ({sub_agent.name}): "
                        f"requires payment_path='{required_payment_path}', got '{actual_payment_path}'. "
                        "Skipping to end of sequence."
                    )
                    if hasattr(ctx, "session") and hasattr(ctx.session, "state"):
                        ctx.session.state["current_stage_index"] = len(self.sub_agents)
                    break

            # Clear termination flag before running the next agent
            if hasattr(ctx, "session") and hasattr(ctx.session, "state"):
                ctx.session.state["_should_terminate_agent"] = False

            # NEW: Trigger introduction if we just transitioned stages mid-session
            if i > 0 and i == current_stage_index:
                if hasattr(ctx, "live_request_queue") and ctx.live_request_queue:
                    from google.genai import types
                    from google.adk.agents.live_request_queue import LiveRequest
                    logger.info(f"💉 Injecting transition trigger for {sub_agent.name}")
                    trigger_req = LiveRequest(
                        content=types.Content(
                            role="user",
                            parts=[types.Part(text=f"SYSTEM_NOTE: Stage transition confirmed. You are now in Stage {i}. Please deliver your stage introduction immediately.")]
                        )
                    )
                    ctx.live_request_queue.send(trigger_req)

            async with Aclosing(sub_agent.run_live(ctx)) as agen:
                async for event in agen:
                    yield event
                    if hasattr(ctx, "session") and hasattr(ctx.session, "state") and ctx.session.state.get("_should_terminate_agent"):
                        logger.info(f"🛑 Terminating {sub_agent.name} loop due to stage advancement.")
                        break
        
        # Log when all stages are complete
        if hasattr(ctx, "session") and hasattr(ctx.session, "state"):
            current_stage_index = ctx.session.state.get("current_stage_index", 0)
            if current_stage_index >= len(self.sub_agents):
                logger.info(f"🏁 All stages complete (index {current_stage_index}).")
