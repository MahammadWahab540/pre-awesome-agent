import json
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .agents.trigger_analyzer import trigger_analyzer
from .agents.visualizer import viz_agent

async def generate_visualization(context: CallbackContext, viz_data: dict):
    """
    Generates a visualization artifact based on the analyzed intent.
    """
    viz_intent = viz_data.get("intent")
    
    # Dynamic Prompt Construction based on Intent
    if viz_intent == "STAGE_SUMMARY_CARD":
        # If a stage just finished, we want to show a summary of what was locked in.
        # We pull the data from the 'output_key' of the agent that just finished.
        stage_name = context.agent_name
        # Attempt to get data from state using the agent name (assuming output_key matches agent name or similar convention)
        # In the Consultant definition, output_key is explicit. 
        # But here context.agent_name is the agent's name.
        # We might need to check the state for the key that matches the agent's output_key.
        # For now, we'll try to use the agent name or look for it in the data provided by analyzer if any.
        # The user's example used: summary_data = context.state.get(stage_name, "No data found for this stage.")
        summary_data = context.state.get(stage_name, "No data found for this stage.")
        
        prompt = f"""
        **Intent:** Generate a 'Stage Completion' Dashboard Card.
        **Stage:** {stage_name}
        **Validated Data to Display:** {summary_data}
        
        **Design Requirement:** Create a celebratory but professional HTML card 
        showing a checkbox marked 'Complete' and a summary list of the validated data.
        """
        
    elif viz_intent == "PROCESS_FLOW":
        prompt = f"Generate a mermaid.js or CSS flowchart for: {viz_data.get('data')}"
        
    elif viz_intent == "RISK_CARD":
        prompt = f"Generate a high-alert HTML card highlighting this risk: {viz_data.get('data')}"
        
    else:
        # Default fallback
        prompt = f"Visualize this data: {viz_data}"

    # We use the 'generate_content' pattern for a quick side-car generation
    # without disrupting the main runner flow.
    # We use the pre-instantiated viz_agent which has the base instruction.
    response = await viz_agent.llm.generate_content_async(
        model=viz_agent.model,
        contents=prompt,
        config=viz_agent.config
    )
    
    html_content = response.text

    # 3. Save as Artifact
    # The UI will detect this via the artifact_delta event.
    filename = f"viz_{viz_intent.lower()}_{context.invocation_id[:4]}.html"
    await context.save_artifact(filename, types.Part(text=html_content))
    print(f"[Visualizer] Generated {filename} for intent {viz_intent}")

async def intelligent_trigger_callback(context: CallbackContext, response):
    """
    Intelligent Trigger Callback that monitors the conversation and triggers visualization.
    """
    # A. Capture the Context
    # Get last user message (simplified retrieval from history)
    last_user_message = "..." 
    if context.events:
        for event in reversed(context.events):
            if event.author == "user":
                last_user_message = event.content.parts.text
                break
            
    current_agent_response = response.content.parts.text if response and response.content else ""
    
    # B. Construct the Analytical Payload
    analysis_input = f"""
    Current Stage: {context.agent_name}
    User Said: "{last_user_message}"
    Agent Replied: "{current_agent_response}"
    """

    # C. Invoke the Shadow Agent (The "Intelligence")
    print(f"\n[Trigger] Analyzing exchange for visualization potential...")
    
    analysis_result = await trigger_analyzer.llm.generate_content_async(
        model=trigger_analyzer.model,
        contents=analysis_input,
        config=trigger_analyzer.config
    )
    
    result_text = analysis_result.text.strip()

    # D. Evaluate the Decision
    if result_text == "NO_ACTION":
        # Fallback: Check for length-based trigger
        if len(current_agent_response) > 100:
            print(f"[Trigger] Response length ({len(current_agent_response)}) > 100 chars. Triggering fallback visualization.")
            # Create a synthetic viz_data for the fallback
            viz_data = {
                "intent": "GENERAL_VISUALIZATION",
                "data": current_agent_response,
                "reasoning": "Response length exceeded 100 characters."
            }
            await generate_visualization(context, viz_data)
            return

        # print("[Trigger] No visualization required.")
        return # Do nothing, let the conversation continue.

    # E. Action: Trigger the Visualizer
    try:
        # Clean up result_text if it contains markdown code blocks
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        viz_data = json.loads(result_text)
        print(f"[Trigger] DETECTED {viz_data.get('intent')}: {viz_data.get('reasoning')}")
        
        # Now we call the Real-Time Visualization Agent with this structured data
        await generate_visualization(context, viz_data)
        
    except json.JSONDecodeError:
        print(f"[Trigger] Error parsing analyzer JSON: {result_text}")

    # Save to memory (Persist Session)
    # We ensure the session is saved after every turn, even if no visualization was triggered
    try:
        memory_service = context._invocation_context.memory_service
        if memory_service:
            await memory_service.add_session_to_memory(context._invocation_context.session)
            # print("💾 Session saved to Memory Bank")
    except Exception as e:
        print(f"⚠️  Memory save warning: {e}")
