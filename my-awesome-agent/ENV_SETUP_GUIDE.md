# .env Configuration Guide for Multimodal Live Agent

## Quick Setup (Copy this to your .env file)

```bash
# 1. Google AI Configuration (REQUIRED)
# Project ID (will auto-detect from gcloud if not set)
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=asia-south1
# GOOGLE_GENAI_USE_VERTEXAI=True

# Gemini Model Name (Optional - defaults to gemini-live-2.5-flash-preview-native-audio-09-2025)
# GEMINI_MODEL_NAME=gemini-live-2.5-flash-preview-native-audio-09-2025

# 2. Database Configuration
# Set to TRUE to use local SQLite, FALSE to use PostgreSQL
USE_LOCAL_DB=TRUE

# PostgreSQL Database URL (only needed if USE_LOCAL_DB=FALSE)
# Format: postgresql+asyncpg://user:password@host:port/database
# DATABASE_URL=postgresql+asyncpg://localhost:5432/adk_sessions

# 3. Vertex AI Memory Bank Configuration (Optional)
# If not set, will fall back to InMemoryMemoryService
# Get this from: gcloud ai agent-engines list --location=asia-south1
# AGENT_ENGINE_ID=your-agent-engine-id
# VERTEX_AI_PROJECT_ID=your-project-id
# VERTEX_AI_LOCATION=asia-south1

# 4. GCS Bucket for Logs (Optional)
# LOGS_BUCKET_NAME=your-logs-bucket-name
```

## Setup Instructions

### Step 1: Google Cloud Authentication

The agent uses Vertex AI and requires Google Cloud authentication:

```bash
# Install gcloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

# Authenticate with Google Cloud
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Set Up Database (Choose ONE)

#### Option A: Local SQLite (Quick Start - DEFAULT)

No setup needed! Just set `USE_LOCAL_DB=TRUE` in your .env file (or leave it unset).
A local database file `local_chat.db` will be created automatically.

#### Option B: PostgreSQL (Production)

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL
sudo service postgresql start

# Create database
sudo -u postgres createdb adk_sessions

# Set in .env:
USE_LOCAL_DB=FALSE
DATABASE_URL=postgresql+asyncpg://localhost:5432/adk_sessions
```

### Step 3: Set Up Vertex AI Memory Bank (Optional)

The memory bank enables long-term memory across sessions. If not configured, the agent will use in-memory storage (memory only lasts during the session).

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Create an Agent Engine (required for Memory Bank)
gcloud alpha ai agent-engines create my-agent-engine \
  --location=asia-south1 \
  --project=YOUR_PROJECT_ID

# List to get the Agent Engine ID
gcloud alpha ai agent-engines list --location=asia-south1

# Add to .env:
AGENT_ENGINE_ID=your-agent-engine-id-from-above
VERTEX_AI_PROJECT_ID=YOUR_PROJECT_ID
VERTEX_AI_LOCATION=asia-south1
```

### Step 4: Install Dependencies

```bash
cd my-awesome-agent

# Install uv if not already installed
pip install uv

# Install dependencies
uv sync

# Or use pip directly
pip install -e .
```

### Step 5: Run the Application

```bash
# Run the FastAPI backend
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000

# Or use the Makefile (if available)
make run
```

The application will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:8000/ (if frontend is built)
- WebSocket endpoint: ws://localhost:8000/ws

## Troubleshooting

### PostgreSQL Connection Issues

If you get connection errors:

```bash
# Check if PostgreSQL is running
sudo service postgresql status

# Check if database exists
sudo -u postgres psql -l | grep adk_sessions

# Create database if missing
sudo -u postgres createdb adk_sessions
```

### Vertex AI Memory Bank Errors

If memory bank initialization fails, the app will continue with InMemoryMemoryService (no long-term memory). To fix:

```bash
# Check if API is enabled
gcloud services list --enabled | grep aiplatform

# Enable if needed
gcloud services enable aiplatform.googleapis.com

# Verify agent engines exist
gcloud alpha ai agent-engines list --location=asia-south1

# Create if missing
gcloud alpha ai agent-engines create my-agent-engine \
  --location=asia-south1
```

### Authentication Issues

If you see authentication errors:

```bash
# Re-authenticate
gcloud auth application-default login

# Verify credentials
gcloud auth application-default print-access-token
```

## Minimal Working Configuration

For a quick test with local database and no long-term memory:

**Create a `.env` file with:**
```bash
USE_LOCAL_DB=TRUE
```

Or simply run without any .env file - the defaults will work!

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_LOCAL_DB` | No | `TRUE` | Use SQLite locally vs PostgreSQL |
| `DATABASE_URL` | Only if `USE_LOCAL_DB=FALSE` | - | PostgreSQL connection string |
| `AGENT_ENGINE_ID` | No | - | Vertex AI Agent Engine for Memory Bank |
| `VERTEX_AI_PROJECT_ID` | No | Auto-detected | Google Cloud Project ID |
| `VERTEX_AI_LOCATION` | No | `asia-south1` | Vertex AI region |
| `GOOGLE_CLOUD_PROJECT` | No | Auto-detected | Google Cloud Project ID |
| `GOOGLE_CLOUD_LOCATION` | No | `asia-south1` | Google Cloud region |
| `GOOGLE_GENAI_USE_VERTEXAI` | No | `True` | Use Vertex AI vs AI Studio |
| `GEMINI_MODEL_NAME` | No | `gemini-live-2.5-flash-preview-native-audio-09-2025` | Gemini model to use for agents |
| `LOGS_BUCKET_NAME` | No | - | GCS bucket for artifact storage |

## Testing the Setup

Once running, you can test the WebSocket connection:

```bash
# Install wscat if needed
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws

# Send a test message (after connection)
{"user_id": "test_user", "live_request": {"text": "Hello!"}}
```

Or open http://localhost:8000 in your browser if the frontend is built.

