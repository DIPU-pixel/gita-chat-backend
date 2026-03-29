# ─────────────────────────────────────────
# payment.py - Razorpay Payment Routes
# ─────────────────────────────────────────

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, User, Payment
from datetime import datetime, timedelta
import razorpay
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET)
)

router = APIRouter(prefix="/payment", tags=["Payment"])

# ─── PLANS ───

PLANS = {
    "daily": {
        "name": "Daily Plan",
        "amount": 10000,      # ₹100 in paise (100 * 100)
        "days": 1,
        "description": "1 Day Unlimited Access"
    },
    "monthly": {
        "name": "Monthly Plan",
        "amount": 19900,      # ₹199 in paise (199 * 100)
        "days": 30,
        "description": "30 Days Unlimited Access"
    }
}

# ─── REQUEST MODELS ───

class CreateOrderRequest(BaseModel):
    plan: str    # "daily" or "monthly"

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: str

# ─── ROUTES ───

@router.get("/plans")
def get_plans():
    """Get all available plans"""
    return {
        "plans": [
            {
                "id": "daily",
                "name": "Daily Plan",
                "amount": 100,
                "currency": "INR",
                "days": 1,
                "description": "1 Day Unlimited Access",
                "features": [
                    "Unlimited questions for 1 day",
                    "All Hindu scriptures",
                    "Hindi + English support",
                    "No ads"
                ]
            },
            {
                "id": "monthly",
                "name": "Monthly Plan",
                "amount": 199,
                "currency": "INR",
                "days": 30,
                "description": "30 Days Unlimited Access",
                "features": [
                    "Unlimited questions for 30 days",
                    "All Hindu scriptures",
                    "Hindi + English + Sanskrit",
                    "No ads",
                    "Priority support",
                    "Best value! 🌟"
                ]
            }
        ]
    }


@router.post("/create-order")
def create_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db)
):
    """Create Razorpay order"""

    # Validate plan
    if request.plan not in PLANS:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan! Choose 'daily' or 'monthly'"
        )

    plan = PLANS[request.plan]

    try:
        # Create Razorpay order
        order = razorpay_client.order.create({
            "amount": plan["amount"],
            "currency": "INR",
            "payment_capture": 1,   # Auto capture payment
            "notes": {
                "plan": request.plan,
                "description": plan["description"]
            }
        })

        return {
            "order_id": order["id"],
            "amount": plan["amount"],
            "currency": "INR",
            "plan": request.plan,
            "plan_name": plan["name"],
            "description": plan["description"],
            "key_id": RAZORPAY_KEY_ID   # Frontend needs this
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create order: {str(e)}"
        )


@router.post("/verify")
def verify_payment(
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db)
):
    """Verify payment and upgrade user"""

    try:
        # Step 1: Verify signature (security check!)
        message = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        expected_signature = hmac.new(
            RAZORPAY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected_signature != request.razorpay_signature:
            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature! Payment verification failed."
            )

        # Step 2: Get plan details
        if request.plan not in PLANS:
            raise HTTPException(
                status_code=400,
                detail="Invalid plan!"
            )

        plan = PLANS[request.plan]

        # Step 3: Get order details from Razorpay
        order = razorpay_client.order.fetch(request.razorpay_order_id)
        user_email = order.get("notes", {}).get("email", "")

        return {
            "message": "Payment verified successfully! 🙏",
            "plan": request.plan,
            "days": plan["days"],
            "order_id": request.razorpay_order_id,
            "payment_id": request.razorpay_payment_id,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment verification failed: {str(e)}"
        )


@router.post("/verify-and-upgrade")
def verify_and_upgrade(
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db)
):
    """Verify payment AND upgrade user in one step"""

    try:
        # Step 1: Verify signature
        message = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        expected_signature = hmac.new(
            RAZORPAY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected_signature != request.razorpay_signature:
            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature!"
            )

        # Step 2: Get plan
        if request.plan not in PLANS:
            raise HTTPException(status_code=400, detail="Invalid plan!")

        plan = PLANS[request.plan]

        # Step 3: Save payment record
        payment = Payment(
            user_id=0,              # Will update below
            user_email="unknown",   # Will update below
            plan=request.plan,
            amount=plan["amount"],
            currency="INR",
            status="success",
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature
        )
        db.add(payment)
        db.commit()

        return {
            "message": "🎉 Payment successful! Account upgraded!",
            "plan": request.plan,
            "plan_name": plan["name"],
            "days": plan["days"],
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )