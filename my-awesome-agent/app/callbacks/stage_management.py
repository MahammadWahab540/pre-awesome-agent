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
    
    # EMPTY OUTPUT MIDDLEWARE
    # Check if response is empty (no text, no tool calls)
    if not response or (not response.text and (not hasattr(response, 'function_calls') or not response.function_calls)):
        logging.warning("⚠️ Empty output detected! Applying fallback middleware...")
        
        # Fallback Logic: Re-ask the checkpoint question for the current step
        current_step = context.state.get('current_stage_index', 0)
        
        # Default fallback
        fallback_text = "Is this a good time to briefly understand the program?"
        
        # We can make this dynamic based on the stage configuration if needed
        # For now, simplistic fallback to keep the conversation moving
        if current_step > 0:
             fallback_text = "Could you please confirm if you are ready to proceed?"

        # Modify the response to include the fallback text
        # Note: We are modifying the response object in place or returning a new one
        # Assuming we can just set the text property or return a modified response
        if response:
             # If response object exists but is empty, try to set text
             try:
                 # Check if response is mutable or if we need to create a new one
                 # LlmResponse might be Pydantic or similar
                 response.text = fallback_text
             except Exception as e:
                 logging.error(f"Failed to set fallback text: {e}")
        
        return response

    # Check if response contains tool calls
    if not hasattr(response, 'function_calls') or not response.function_calls:
        return response
    
    for tool_call in response.function_calls:
        tool_name = tool_call.name
        
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

