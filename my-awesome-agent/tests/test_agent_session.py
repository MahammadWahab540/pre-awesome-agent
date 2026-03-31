import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest


def _import_agent_session_module():
    slowapi_module = types.ModuleType("slowapi")
    slowapi_module.Limiter = MagicMock()
    slowapi_module._rate_limit_exceeded_handler = MagicMock()

    slowapi_util_module = types.ModuleType("slowapi.util")
    slowapi_util_module.get_remote_address = MagicMock(return_value="127.0.0.1")

    slowapi_errors_module = types.ModuleType("slowapi.errors")

    class RateLimitExceeded(Exception):
        pass

    slowapi_errors_module.RateLimitExceeded = RateLimitExceeded

    sys.modules["slowapi"] = slowapi_module
    sys.modules["slowapi.util"] = slowapi_util_module
    sys.modules["slowapi.errors"] = slowapi_errors_module
    sys.modules.pop("app.fast_api_app", None)
    return importlib.import_module("app.fast_api_app")


@pytest.mark.asyncio
async def test_clear_resuming_flag_persists_before_forward():
    module = _import_agent_session_module()
    AgentSession = module.AgentSession
    APP_NAME = module.APP_NAME

    websocket = MagicMock()
    session_service = MagicMock()
    latest_session = MagicMock()
    latest_session.state = {"is_resuming": True}
    session_service.get_session = AsyncMock(return_value=latest_session)

    runner = MagicMock()
    runner.app = MagicMock()
    runner.app.name = APP_NAME
    runner.session_service = MagicMock()
    runner.session_service.append_event = AsyncMock()

    session = AgentSession(websocket, session_service, runner, MagicMock())
    session.user_id = "user-1"
    session.session_id = "session-1"
    session.session = latest_session

    await session._clear_resuming_flag_if_needed(APP_NAME)

    runner.session_service.append_event.assert_awaited_once()
    assert latest_session.state["is_resuming"] is False
    assert session.has_cleared_resuming is True


@pytest.mark.asyncio
async def test_clear_resuming_flag_skips_when_already_false():
    module = _import_agent_session_module()
    AgentSession = module.AgentSession
    APP_NAME = module.APP_NAME

    websocket = MagicMock()
    session_service = MagicMock()
    latest_session = MagicMock()
    latest_session.state = {"is_resuming": False}
    session_service.get_session = AsyncMock(return_value=latest_session)

    runner = MagicMock()
    runner.app = MagicMock()
    runner.app.name = APP_NAME
    runner.session_service = MagicMock()
    runner.session_service.append_event = AsyncMock()

    session = AgentSession(websocket, session_service, runner, MagicMock())
    session.user_id = "user-1"
    session.session_id = "session-1"
    session.session = latest_session

    await session._clear_resuming_flag_if_needed(APP_NAME)

    runner.session_service.append_event.assert_not_called()
    assert session.has_cleared_resuming is True
