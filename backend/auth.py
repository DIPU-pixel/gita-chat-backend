from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import User
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
FREE_DAILY_LIMIT = 2

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── PASSWORD ───

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── JWT TOKEN ───

def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    data = {"sub": str(user_id), "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except JWTError:
        return None

# ─── USER ───

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, name: str, email: str, password: str):
    hashed = hash_password(password)
    user = User(
        name=name,
        email=email,
        password=hashed,
        plan="free",
        questions_today=0,
        last_reset_date=str(datetime.utcnow().date())
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ─── DAILY LIMIT ───

def check_and_reset_limit(db: Session, user: User):
    """Reset daily count if new day"""
    today = str(datetime.utcnow().date())
    if user.last_reset_date != today:
        user.questions_today = 0
        user.last_reset_date = today
        db.commit()
        db.refresh(user)
    return user

def can_ask_question(user: User) -> bool:
    """Check if user can ask more questions"""
    if user.plan == "premium":
        return True
    return user.questions_today < FREE_DAILY_LIMIT

def increment_question_count(db: Session, user: User):
    """Add 1 to today's question count"""
    user.questions_today += 1
    db.commit()

def get_remaining_questions(user: User) -> int:
    """How many questions left today"""
    if user.plan == "premium":
        return 999
    return max(0, FREE_DAILY_LIMIT - user.questions_today)