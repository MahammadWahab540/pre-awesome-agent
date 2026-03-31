"""Tests for the sequential agent live-tool patching behavior."""

from google.adk.agents import LlmAgent

from app.agents.patched_sequential_agent import PatchedSequentialAgent


def _make_llm_agent(name: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model="gemini-2.0-flash",
        instruction="Follow the stage instructions exactly.",
        tools=[],
    )


def _tool_names(agent: LlmAgent) -> list[str]:
    names: list[str] = []
    for tool in agent.tools:
        tool_name = getattr(tool, "name", None) or getattr(tool, "__name__", "")
        if isinstance(tool_name, str):
            names.append(tool_name)
    return names


def test_task_completed_tool_is_enabled_by_default():
    sub_agent = _make_llm_agent("stage_0_agent")

    PatchedSequentialAgent(name="orchestrator", sub_agents=[sub_agent])

    assert "task_completed" in _tool_names(sub_agent)
    assert "call the task_completed function" in sub_agent.instruction


def test_task_completed_tool_can_be_disabled():
    sub_agent = _make_llm_agent("stage_0_agent")

    PatchedSequentialAgent(
        name="orchestrator",
        sub_agents=[sub_agent],
        enable_task_completed_tool=False,
    )

    assert "task_completed" not in _tool_names(sub_agent)
    assert "call the task_completed function" not in sub_agent.instruction
