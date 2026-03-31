"""Tests for stage management tools — focused on the is_resuming guard and payment path logic."""
import pytest
from unittest.mock import MagicMock, patch


def _make_tool_context(state: dict) -> MagicMock:
    """Build a minimal ToolContext mock with a mutable state dict."""
    ctx = MagicMock()
    ctx.state = state
    ctx.session = MagicMock()
    ctx.session.id = "test-session-id"
    return ctx


# ---------------------------------------------------------------------------
# complete_program_explanation
# ---------------------------------------------------------------------------

class TestCompleteProgramExplanation:

    def test_blocks_when_resuming(self):
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context({"is_resuming": True, "current_stage_index": 0})
        result = complete_program_explanation(ctx, payment_path="full_payment")

        assert "SYSTEM_NOTE" in result
        assert "resuming" in result.lower() or "resumed" in result.lower()
        # Stage must NOT have been advanced
        assert ctx.state.get("current_stage_index") == 0
        assert ctx.state.get("_should_terminate_agent") is not True

    def test_blocks_invalid_payment_path(self):
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        result = complete_program_explanation(ctx, payment_path="bitcoin")

        assert "SYSTEM_NOTE" in result
        assert ctx.state.get("current_stage_index") == 0

    def test_blocks_empty_payment_path(self):
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        result = complete_program_explanation(ctx, payment_path="")

        assert "SYSTEM_NOTE" in result
        assert ctx.state.get("current_stage_index") == 0

    def test_blocks_repeat_confirmation_after_success(self):
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context(
            {
                "is_resuming": False,
                "current_stage_index": 0,
                "stage_1_confirmed": True,
            }
        )
        result = complete_program_explanation(ctx, payment_path="emi")

        assert "SYSTEM_NOTE" in result
        assert "already been completed" in result
        assert ctx.state.get("current_stage_index") == 0

    @patch("app.agents.tools.advance_stage")
    def test_full_payment_skips_to_stage_2(self, mock_advance):
        mock_advance.return_value = "SYSTEM_NOTE: Stage 0 advanced to 2."
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        complete_program_explanation(ctx, payment_path="full_payment")

        mock_advance.assert_called_once_with(ctx, 0, next_index=2)
        assert ctx.state["payment_path"] == "full_payment"

    @patch("app.agents.tools.advance_stage")
    def test_credit_card_skips_to_stage_2(self, mock_advance):
        mock_advance.return_value = "SYSTEM_NOTE: Stage 0 advanced to 2."
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        complete_program_explanation(ctx, payment_path="credit_card")

        mock_advance.assert_called_once_with(ctx, 0, next_index=2)
        assert ctx.state["payment_path"] == "credit_card"

    @patch("app.agents.tools.advance_stage")
    def test_emi_goes_to_stage_1(self, mock_advance):
        mock_advance.return_value = "SYSTEM_NOTE: Stage 0 advanced to 1."
        from app.agents.tools import complete_program_explanation

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        complete_program_explanation(ctx, payment_path="emi")

        mock_advance.assert_called_once_with(ctx, 0, next_index=None)
        assert ctx.state["payment_path"] == "emi"


# ---------------------------------------------------------------------------
# advance_stage
# ---------------------------------------------------------------------------

class TestAdvanceStage:

    def test_blocks_when_resuming(self):
        from app.agents.tools import advance_stage

        ctx = _make_tool_context({"is_resuming": True, "current_stage_index": 0})
        result = advance_stage(ctx, stage_index=0)

        assert "SYSTEM_NOTE" in result
        # Stage must NOT have advanced
        assert ctx.state["current_stage_index"] == 0
        assert ctx.state.get("_should_terminate_agent") is not True

    def test_hallucination_guard_wrong_stage(self):
        from app.agents.tools import advance_stage

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 1})
        result = advance_stage(ctx, stage_index=0)

        assert "SYSTEM_NOTE" in result
        # Stage must NOT have changed
        assert ctx.state["current_stage_index"] == 1

    def test_normal_advance(self):
        from app.agents.tools import advance_stage

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            result = advance_stage(ctx, stage_index=0)

        assert "advanced to 1" in result
        assert ctx.state["current_stage_index"] == 1
        assert ctx.state["_should_terminate_agent"] is True

    def test_advance_with_custom_next_index(self):
        from app.agents.tools import advance_stage

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            result = advance_stage(ctx, stage_index=0, next_index=2)

        assert "advanced to 2" in result
        assert ctx.state["current_stage_index"] == 2


class TestContinuousConversation:

    def test_resuming_note_does_not_advance_stage(self):
        from app.agents.tools import continuous_conversation

        ctx = _make_tool_context({"is_resuming": True, "current_stage_index": 1})
        result = continuous_conversation(ctx)

        assert "SYSTEM_NOTE" in result
        assert "resuming" in result.lower()
        assert ctx.state["current_stage_index"] == 1

    def test_active_session_returns_continue_note(self):
        from app.agents.tools import continuous_conversation

        ctx = _make_tool_context({"is_resuming": False, "current_stage_index": 0})
        result = continuous_conversation(ctx)

        assert "SYSTEM_NOTE" in result
        assert "continue the current stage conversation" in result.lower()
        assert ctx.state["current_stage_index"] == 0


# ---------------------------------------------------------------------------
# Session reconnect state logic (is_resuming flag initialization)
# ---------------------------------------------------------------------------

class TestSessionReconnectStateLogic:
    """
    Tests for the state_delta construction logic in fast_api_app.py.
    The key rule: is_resuming=True when reconnecting to an existing session,
    is_resuming=False for brand-new sessions.
    """

    def _build_state_delta(self, existing_state: dict) -> dict:
        """Mirror the state_delta logic from fast_api_app.py for unit testing."""
        is_reconnect = "current_stage_index" in existing_state
        state_delta = {
            "user_name": "Test User",
            "user_language": "en-US",
            **(
                {} if is_reconnect else {"current_stage_index": 0}
            ),
            **(
                {} if "payment_path" in existing_state else {"payment_path": ""}
            ),
            **(
                {"is_resuming": True} if is_reconnect else {"is_resuming": False}
            ),
        }
        return state_delta

    def test_new_session_sets_is_resuming_false(self):
        existing_state = {}  # brand new session
        delta = self._build_state_delta(existing_state)

        assert delta["is_resuming"] is False
        assert delta["current_stage_index"] == 0
        assert delta["payment_path"] == ""

    def test_reconnect_sets_is_resuming_true(self):
        existing_state = {"current_stage_index": 0, "payment_path": ""}
        delta = self._build_state_delta(existing_state)

        assert delta["is_resuming"] is True
        assert "current_stage_index" not in delta  # preserved, not overwritten

    def test_reconnect_preserves_payment_path(self):
        existing_state = {"current_stage_index": 0, "payment_path": "full_payment"}
        delta = self._build_state_delta(existing_state)

        assert delta["is_resuming"] is True
        assert "payment_path" not in delta  # preserved, not overwritten

    def test_reconnect_mid_session(self):
        existing_state = {"current_stage_index": 1, "payment_path": "emi"}
        delta = self._build_state_delta(existing_state)

        assert delta["is_resuming"] is True
        assert "current_stage_index" not in delta
