from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from backend.models import SessionState, ChatRequest, ChatResponse
from backend.rag import load_menu
from backend.graph_app import run_turn

app = FastAPI(title="AI Restaurant Assistant API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
SESSIONS: Dict[str, SessionState] = {}


@app.get("/")
def root():
    return {"message": "AI Restaurant Assistant API", "status": "running"}


@app.get("/menu")
def get_menu():
    """Get full menu."""
    return load_menu()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Handle chat interaction."""
    # Get or create session
    state = SESSIONS.get(req.session_id, SessionState())
    
    # Set allergens if provided
    if req.user_allergens:
        state.allergens = [a.lower().strip() for a in req.user_allergens]
    
    # Process turn
    state, assistant_message = run_turn(
        state,
        req.user_message,
        user_email=req.user_email
    )
    
    # Save session
    SESSIONS[req.session_id] = state
    
    return ChatResponse(
        assistant_message=assistant_message,
        current_order=state.current_order,
        current_total=state.current_total,
    )


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Clear a session."""
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        return {"message": "Session cleared"}
    return {"message": "Session not found"}
