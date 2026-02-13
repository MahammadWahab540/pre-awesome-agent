"""SequentialAgent wrapper with stable live-mode tool registration."""

from __future__ import annotations

import inspect
from typing import Any
from typing import AsyncGenerator
from typing import Callable

from typing_extensions import override

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events.event import Event
from google.adk.tools import ToolContext
from google.adk.utils.context_utils import Aclosing

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
    """SequentialAgent with deterministic task_completed tool handling."""

    @override
    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

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
                return "Task completion signaled."

            # Remove stale duplicates (including pre-existing buggy state), then
            # append a single canonical task_completed tool.
            tools_without_task_completed = [
                tool
                for tool in sub_agent.tools
                if _tool_name(tool) != _TASK_COMPLETED_TOOL_NAME
            ]
            tools_without_task_completed.append(task_completed)
            sub_agent.tools = _dedupe_tools_by_name(tools_without_task_completed)

            sub_agent.instruction = _ensure_task_completed_instruction(
                sub_agent.instruction
            )

        for sub_agent in self.sub_agents:
            async with Aclosing(sub_agent.run_live(ctx)) as agen:
                async for event in agen:
                    yield event
