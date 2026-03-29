# ─────────────────────────────────────────
# admin.py - Admin Routes
# ─────────────────────────────────────────

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, User, Payment
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_SECRET = os.getenv("ADMIN_SECRET")

router = APIRouter(prefix="/admin", tags=["Admin"])

# ─── REQUEST MODELS ───

class UpgradeRequest(BaseModel):
    email: str
    plan: str        # "premium"
    days: int        # how many days
    admin_secret: str

class DowngradeRequest(BaseModel):
    email: str
    admin_secret: str

class AdminSecretRequest(BaseModel):
    admin_secret: str

# ─── HELPER ───

def verify_admin(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin secret! Access denied."
        )

# ─── ROUTES ───

@router.post("/upgrade-user")
def upgrade_user(
    request: UpgradeRequest,
    db: Session = Depends(get_db)
):
    # Verify admin secret
    verify_admin(request.admin_secret)

    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with email {request.email} not found!"
        )

    # Upgrade user
    user.plan = request.plan
    user.subscription_end = datetime.utcnow() + timedelta(days=request.days)
    db.commit()
    db.refresh(user)

    return {
        "message": f"✅ User upgraded successfully!",
        "user": {
            "name": user.name,
            "email": user.email,
            "plan": user.plan,
            "subscription_end": user.subscription_end
        }
    }


@router.post("/downgrade-user")
def downgrade_user(
    request: DowngradeRequest,
    db: Session = Depends(get_db)
):
    # Verify admin secret
    verify_admin(request.admin_secret)

    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {request.email} not found!"
        )

    # Downgrade
    user.plan = "free"
    user.subscription_end = None
    db.commit()

    return {
        "message": f"✅ User downgraded to free!",
        "email": user.email,
        "plan": user.plan
    }


@router.post("/users")
def get_all_users(
    request: AdminSecretRequest,
    db: Session = Depends(get_db)
):
    # Verify admin secret
    verify_admin(request.admin_secret)

    users = db.query(User).order_by(User.created_at.desc()).all()

    return {
        "total": len(users),
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "plan": u.plan,
                "questions_today": u.questions_today,
                "subscription_end": u.subscription_end,
                "created_at": u.created_at
            }
            for u in users
        ]
    }


@router.post("/stats")
def get_stats(
    request: AdminSecretRequest,
    db: Session = Depends(get_db)
):
    # Verify admin secret
    verify_admin(request.admin_secret)

    total_users = db.query(User).count()
    free_users = db.query(User).filter(User.plan == "free").count()
    premium_users = db.query(User).filter(User.plan == "premium").count()

    return {
        "total_users": total_users,
        "free_users": free_users,
        "premium_users": premium_users,
    }