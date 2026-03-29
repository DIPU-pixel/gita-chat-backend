# ─────────────────────────────────────────
# main.py - Complete Gita Chat API
# ─────────────────────────────────────────

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from payment import router as payment_router
from typing import Optional, List
from database import get_db, create_tables, ChatHistory, ChatSession
from auth import (
    create_user, get_user_by_email, get_user_by_id,
    verify_password, create_token, decode_token,
    check_and_reset_limit, can_ask_question,
    increment_question_count, get_remaining_questions,
    FREE_DAILY_LIMIT
)
from admin import router as admin_router
from rag import ask_gita
from datetime import datetime
import uvicorn

# Create tables on startup
create_tables()

# ─── APP SETUP ───

app = FastAPI(
    title="🕉️ Gita Chat API",
    description="Chat with Bhagavad Gita powered by RAG + Claude AI",
    version="1.0.0"
)
app.include_router(admin_router)
app.include_router(payment_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REQUEST MODELS ───

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QuestionRequest(BaseModel):
    question: str

# ─── HELPER: Get current logged in user ───

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not logged in. Please login first!"
        )

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please login again!"
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found!"
        )

    return user


# ─── HELPER: Verify session belongs to current user ───

def get_session_for_user(session_id: int, user_id: int, db: Session):
    """Fetch session only if it belongs to this user"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id       # ← data isolation check
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found or you don't have access to it."
        )
    return session


# ─── ROUTES ───

@app.get("/")
def home():
    return {
        "message": "🕉️ Gita Chat API is running!",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")

def health():
    return {"status": "healthy"}

# ──────────────────────────────
# AUTH ROUTES
# ──────────────────────────────

@app.post("/auth/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered! Please login.")

    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters!")

    user = create_user(db, request.name, request.email, request.password)
    token = create_token(user.id)

    return {
        "message": "Account created successfully! 🙏",
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan": user.plan,
            "questions_remaining": FREE_DAILY_LIMIT
        }
    }


@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=400, detail="Email not found! Please register first.")

    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=400, detail="Wrong password! Please try again.")

    token = create_token(user.id)

    return {
        "message": "Login successful! 🙏",
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan": user.plan,
            "questions_remaining": get_remaining_questions(user)
        }
    }


@app.get("/auth/me")
def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = check_and_reset_limit(db, current_user)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "plan": user.plan,
        "questions_today": user.questions_today,
        "questions_remaining": get_remaining_questions(user),
        "daily_limit": FREE_DAILY_LIMIT if user.plan == "free" else "unlimited",
        "subscription_end": user.subscription_end
    }


# ──────────────────────────────
# SESSION ROUTES
# ──────────────────────────────

@app.post("/chat/session/new")
def new_session(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session. Returns session_id to use in /chat/{session_id}"""
    session = ChatSession(
        user_id=current_user.id,
        title="New Chat"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at
    }


@app.get("/chat/sessions")
def get_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all sessions for the current user — for sidebar display"""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(
        ChatSession.updated_at.desc()
    ).all()

    return {
        "sessions": [
            {
                "session_id": s.id,
                "title": s.title,
                "created_at": s.created_at,
                "updated_at": s.updated_at
            }
            for s in sessions
        ]
    }


@app.get("/chat/session/{session_id}")
def get_session_messages(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages inside a session — only if it belongs to current user"""
    # Ownership check
    get_session_for_user(session_id, current_user.id, db)

    messages = db.query(ChatHistory)\
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == current_user.id     # ← double safety check
        )\
        .order_by(ChatHistory.created_at.asc())\
        .all()

    return {
        "session_id": session_id,
        "messages": [
            {
                "id": m.id,
                "question": m.question,
                "answer": m.answer,
                "sources": m.sources,
                "language": m.language,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }


@app.delete("/chat/session/{session_id}")
def delete_session(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a session and all its messages"""
    session = get_session_for_user(session_id, current_user.id, db)

    # Delete all messages in this session first
    db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()

    # Delete the session itself
    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully 🙏"}


# ──────────────────────────────
# CHAT ROUTES
# ──────────────────────────────

@app.post("/chat/{session_id}")
def chat(
    session_id: int,
    request: QuestionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 1: Verify session belongs to this user
    session = get_session_for_user(session_id, current_user.id, db)

    # Step 2: Reset daily limit if new day
    user = check_and_reset_limit(db, current_user)

    # Step 3: Check if user can ask question
    if not can_ask_question(user):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Daily limit reached! Upgrade to Premium for unlimited questions 🙏",
                "questions_used": user.questions_today,
                "limit": FREE_DAILY_LIMIT,
                "plan": user.plan
            }
        )

    # Step 4: Validate question
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty!")

    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question too long! Maximum 500 characters.")

    # Step 5: Load conversation history for this session (last 5 exchanges)
    past_messages = db.query(ChatHistory)\
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == current_user.id
        )\
        .order_by(ChatHistory.created_at.asc())\
        .all()

    conversation_history = [
        {"question": m.question, "answer": m.answer}
        for m in past_messages
    ]

    # Step 6: Get answer from RAG with conversation context
    result = ask_gita(request.question, conversation_history=conversation_history)

    # Step 7: Auto-set session title from first question
    if session.title == "New Chat" and len(past_messages) == 0:
        # Use first 6 words of the question as the title
        words = request.question.strip().split()
        title = " ".join(words[:6])
        if len(words) > 6:
            title += "..."
        session.title = title
        session.updated_at = datetime.utcnow()
        db.commit()

    # Step 8: Update session's updated_at so sidebar shows latest first
    session.updated_at = datetime.utcnow()

    # Step 9: Save message to chat history
    chat_entry = ChatHistory(
        session_id=session_id,
        user_id=user.id,
        question=request.question,
        answer=result['answer'],
        sources=", ".join(result['sources']),
        language=result['language']
    )
    db.add(chat_entry)
    db.commit()

    # Step 10: Crisis messages don't count towards daily limit
    if not result.get('is_crisis', False):
        increment_question_count(db, user)

    # Step 11: Return response
    return {
        "answer": result['answer'],
        "sources": result['sources'],
        "language": result['language'],
        "is_crisis": result.get('is_crisis', False),
        "resources": result.get('resources', []),
        "session_id": session_id,
        "session_title": session.title,
        "questions_remaining": get_remaining_questions(user),
        "status": "success"
    }


# ──────────────────────────────
# USER ROUTES
# ──────────────────────────────

@app.get("/user/history")
def chat_history(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get last 20 messages across ALL sessions for this user"""
    history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == current_user.id)\
        .order_by(ChatHistory.created_at.desc())\
        .limit(20)\
        .all()

    return {
        "history": [
            {
                "session_id": h.session_id,
                "question": h.question,
                "answer": h.answer,
                "sources": h.sources,
                "language": h.language,
                "created_at": h.created_at
            }
            for h in history
        ]
    }


@app.get("/user/usage")
def usage(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = check_and_reset_limit(db, current_user)
    return {
        "plan": user.plan,
        "questions_today": user.questions_today,
        "questions_remaining": get_remaining_questions(user),
        "daily_limit": FREE_DAILY_LIMIT if user.plan == "free" else "unlimited"
    }


# ──────────────────────────────
# RUN SERVER
# ──────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )