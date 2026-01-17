# NxtWave Voice Agent - Program Registration Expert

A multimodal voice agent application for NxtWave's CCBP 4.0 program registration, featuring a 2-stage conversation flow with real-time voice interaction and visual feedback.

## Project Structure

```
PRE_Voice_agent/
├── frontend/              # Next.js frontend application
│   ├── app/              # Next.js app router pages
│   ├── components/       # React components
│   ├── lib/              # Utility libraries
│   └── multimodal-live/  # Multimodal live components
│
└── my-awesome-agent/     # Python backend (ADK-based)
    ├── app/
    │   ├── agents/       # Agent definitions and tools
    │   ├── callbacks/    # Event callbacks
    │   └── instructions/ # Agent instruction files
    └── requirements.txt
```

## Features

- **2-Stage Conversation Flow**
  - Stage 1: Program Explanation (CCBP 4.0 value proposition)
  - Stage 2: Payment Structure (Full Payment vs EMI options)

- **Real-time Voice Interaction**
  - Multimodal live API integration
  - Audio visualization with 3D orb
  - Live transcription display

- **Visual Progress Tracking**
  - Gradient-colored stage indicators
  - Real-time stage progression
  - Completion status tracking

## Tech Stack

### Frontend
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Framer Motion
- Three.js (for visualizations)

### Backend
- Python 3.11+
- Google ADK (Agent Development Kit)
- FastAPI
- Vertex AI / Gemini API
- WebSocket for real-time communication

## Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- Google Cloud Project with Vertex AI enabled
- Firebase project (for session persistence)

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Configure your environment variables
npm run dev
```

### Backend Setup

```bash
cd my-awesome-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure Firebase service account
cp firebase_service_account.example.py firebase_service_account.py
# Edit firebase_service_account.py with your Firebase credentials

# Configure your Google Cloud credentials
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000
```

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_MY_AWESOME_AGENT_URL=ws://localhost:8000/
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
```

### Backend
```
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GOOGLE_CLOUD_LOCATION=asia-south1
GEMINI_MODEL_NAME=gemini-live-2.5-flash-native-audio
```

## Development

- Frontend runs on `http://localhost:9002`
- Backend runs on `http://localhost:8000`
- WebSocket endpoint: `ws://localhost:8000/ws`

## Architecture

The application uses a sequential agent architecture where:
1. `ProgramRegistrationOrchestrator` manages the overall flow
2. `program_explanation_agent` handles Stage 0
3. `payment_structure_agent` handles Stage 1
4. Real-time WebSocket communication for bidirectional audio/data streaming

## License

Private - All Rights Reserved

## Contact

For questions or support, contact the NxtWave development team.
