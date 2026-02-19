"""Callback for handling stage transitions and workflow state."""

import logging
from typing import Any, List

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    content = getattr(response, "content", None)
    parts = getattr(content, "parts", None)
    if not isinstance(parts, list):
        return ""

    text_parts: List[str] = []
    for part in parts:
        part_text = getattr(part, "text", None)
        if isinstance(part_text, str) and part_text.strip():
            text_parts.append(part_text.strip())
    return "\n".join(text_parts).strip()


def _extract_function_calls(response: Any) -> list[Any]:
    function_calls = getattr(response, "function_calls", None)
    if isinstance(function_calls, list):
        return function_calls

    content = getattr(response, "content", None)
    parts = getattr(content, "parts", None)
    if not isinstance(parts, list):
        return []

    calls: list[Any] = []
    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call is not None:
            calls.append(function_call)
    return calls


def _build_fallback_response(fallback_text: str, current_stage_index: int) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=fallback_text)]),
        custom_metadata={"current_stage_index": current_stage_index},
    )


async def stage_management_callback(context: CallbackContext, response):
    """Handle stage transitions when tools are called.
    
    This callback intercepts tool calls to advance_stage and finalize_discovery
    and updates the session state accordingly.
    
    Args:
        context: The callback context with session state access
        response: The LLM response containing tool calls
    """
    
    # EMPTY OUTPUT MIDDLEWARE
    # Check if response is empty (no text, no tool calls)
    response_text = _extract_response_text(response) if response else ""
    response_function_calls = _extract_function_calls(response) if response else []

    if not response or (not response_text and not response_function_calls):
        logging.warning("⚠️ Empty output detected! Applying fallback middleware...")
        
        # Fallback Logic: Re-ask the checkpoint question for the current step
        current_step = context.state.get('current_stage_index', 0)
        
        # Default fallback
        fallback_text = "Is this a good time to briefly understand the program?"
        
        # We can make this dynamic based on the stage configuration if needed
        # For now, simplistic fallback to keep the conversation moving
        if current_step > 0:
             fallback_text = "Could you please confirm if you are ready to proceed?"

        if response is None:
            return _build_fallback_response(fallback_text, current_step)

        # If response object exists but is empty, try to mutate in place.
        try:
            if hasattr(response, 'text'):
                response.text = fallback_text
            else:
                response.content = types.Content(
                    role="model",
                    parts=[types.Part(text=fallback_text)],
                )

            try:
                if hasattr(response, 'function_calls'):
                    response.function_calls = []
            except Exception as e:
                logging.error(f"Failed to reset fallback function calls: {e}")
            return response
        except Exception as e:
            logging.error(f"Failed to set fallback text: {e}")
            return _build_fallback_response(fallback_text, current_step)

    # Check if response contains tool calls
    if not response_function_calls:
        return response
    
    for tool_call in response_function_calls:
        tool_name = getattr(tool_call, "name", "")
        
        if tool_name == "advance_stage":
            # Get current stage index
            current_stage = context.state.get('current_stage_index', 0)
            next_stage = current_stage + 1
            
            # Update state
            context.state['current_stage_index'] = next_stage
            context.state[f'stage_{current_stage}_completed'] = True
            
            logging.info(f"✅ Stage {current_stage} completed. Moving to stage {next_stage} (Index: {next_stage})")
            
        elif tool_name == "finalize_discovery":
            # Mark workflow as complete
            context.state['workflow_status'] = 'COMPLETED'
            context.state['discovery_completed'] = True
            context.state['current_stage_index'] = 7  # Beyond last stage
            
            logging.info("✅ Discovery process finalized. Ready for BRD generation.")
    
    return response

