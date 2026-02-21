# Copyright 2025 Google LLC
# ... (License Header) ...

"""
Multimodal Live Agent with DatabaseSessionService and VertexAiMemoryBankService
"""
import os
from dotenv import load_dotenv
import vertexai

# ==============================================================================
# ENVIRONMENT SETUP
# ==============================================================================
load_dotenv()

# ==============================================================================
# FORCE VERTEX AI LOCATION TO US-CENTRAL1
# ==============================================================================
# This overrides Cloud Run's auto-detection of 'asia-south1'
# The gemini-live-*-native-audio models are only available in us-central1
vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")  # Force US region regardless of where Cloud Run is deployed
)

from google.adk.apps.app import App

# Live-mode task_completed dedupe is handled by PatchedSequentialAgent in
# app/agents/patched_sequential_agent.py.

# ==============================================================================
# AGENT IMPORT (Updated)
# ==============================================================================
# UPDATED: Import the factory function to create agent instances
from .agents.consultant import get_consultant_agent

APP_NAME = "app"


def create_app() -> App:
    """Create a new ADK App with a fresh consultant agent tree."""
    return App(root_agent=get_consultant_agent(), name=APP_NAME)
