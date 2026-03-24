# ─────────────────────────────────────────
# main.py - Complete Gita Chat API
# ─────────────────────────────────────────

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db, create_tables, ChatHistory
from auth import (
    create_user, get_user_by_email, get_user_by_id,
    verify_password, create_token, decode_token,
    check_and_reset_limit, can_ask_question,
    increment_question_count, get_remaining_questions,
    FREE_DAILY_LIMIT
)
from rag import ask_gita
import uvicorn

# Create tables on startup
create_tables()

# ─── APP SETUP ───

app = FastAPI(
    title="🕉️ Gita Chat API",
    description="Chat with Bhagavad Gita powered by RAG + Claude AI",
    version="1.0.0"
)

# Allow frontend to connect
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

# ─── HELPER ───

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
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing = get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered! Please login."
        )

    # Validate password length
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters!"
        )

    # Create user
    user = create_user(
        db,
        request.name,
        request.email,
        request.password
    )
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
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    # Find user
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email not found! Please register first."
        )

    # Check password
    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=400,
            detail="Wrong password! Please try again."
        )

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
def get_me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
# CHAT ROUTES
# ──────────────────────────────

@app.post("/chat")
def chat(
    request: QuestionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Step 1: Reset daily limit if new day
    user = check_and_reset_limit(db, current_user)

    # Step 2: Check if user can ask question
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

    # Step 3: Validate question
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty!"
        )

    if len(request.question) > 500:
        raise HTTPException(
            status_code=400,
            detail="Question too long! Maximum 500 characters."
        )

    # Step 4: Get answer from RAG
    result = ask_gita(request.question)

    # Step 5: Save to chat history
    chat_entry = ChatHistory(
        user_id=user.id,
        question=request.question,
        answer=result['answer'],
        sources=", ".join(result['sources']),
        language=result['language']
    )
    db.add(chat_entry)
    db.commit()

    # Step 6: Crisis messages don't count towards daily limit
    if not result.get('is_crisis', False):
        increment_question_count(db, user)

    # Step 7: Return response
    return {
        "answer": result['answer'],
        "sources": result['sources'],
        "language": result['language'],
        "is_crisis": result.get('is_crisis', False),
        "resources": result.get('resources', []),
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
    history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == current_user.id)\
        .order_by(ChatHistory.created_at.desc())\
        .limit(20)\
        .all()

    return {
        "history": [
            {
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