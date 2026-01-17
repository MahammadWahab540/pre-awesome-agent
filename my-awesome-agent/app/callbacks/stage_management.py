"""Callback for handling stage transitions and workflow state."""

import logging
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions


async def stage_management_callback(context: CallbackContext, response):
    """Handle stage transitions when tools are called.
    
    This callback intercepts tool calls to advance_stage and finalize_discovery
    and updates the session state accordingly.
    
    Args:
        context: The callback context with session state access
        response: The LLM response containing tool calls
    """
    
    # Check if response contains tool calls
    if not hasattr(response, 'function_calls') or not response.function_calls:
        return response
    
    for tool_call in response.function_calls:
        tool_name = tool_call.name
        
        if tool_name == "advance_stage":
            # Get current stage and advance it
            current_stage = context.state.get('current_stage', 0)
            next_stage = current_stage + 1
            
            # Update state
            context.state['current_stage'] = next_stage
            context.state[f'stage_{current_stage}_completed'] = True
            
            logging.info(f"✅ Stage {current_stage} completed. Moving to stage {next_stage}")
            
        elif tool_name == "finalize_discovery":
            # Mark workflow as complete
            context.state['workflow_status'] = 'COMPLETED'
            context.state['discovery_completed'] = True
            context.state['current_stage'] = 7  # Beyond last stage
            
            logging.info("✅ Discovery process finalized. Ready for BRD generation.")
    
    return response

