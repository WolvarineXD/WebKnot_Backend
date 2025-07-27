import re
import random
import string
from fastapi import APIRouter, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user_model import UserSignupInit, UserVerifyOTP, UserLogin
from db import users_collection,otp_collection
from utils import hash_password, verify_password, create_access_token, send_email_otp, decode_access_token
from bson import ObjectId

router = APIRouter(prefix="/auth")
security = HTTPBearer()

# ✅ Password strength validator
def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"\d", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

# ✅ OTP generator
def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

@router.post("/signup/init")
async def signup_init(user: UserSignupInit):
    if not user.email.strip().lower().endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Only WebKnot Gmail addresses are allowed.")

    if not is_strong_password(user.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters, include a digit and a special character."
        )

    existing = await users_collection.find_one({"email": user.email.strip().lower()})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists.")

    async for existing_user in users_collection.find({}):
        if verify_password(user.password, existing_user["password"]):
            raise HTTPException(status_code=400, detail="Password already in use. Please choose a different one.")

    otp = generate_otp()
    await send_email_otp(user.email.strip().lower(), otp)

    await otp_collection.insert_one({
        "email": user.email.strip().lower(),
        "name": user.name.strip(),
        "password": hash_password(user.password),
        "otp": otp
    })

    return {"message": f"OTP sent to {user.email}. Please verify to complete signup."}

@router.post("/signup/verify")
async def verify_signup(data: UserVerifyOTP):
    record = await otp_collection.find_one({
        "email": data.email.strip().lower(),
        "otp": data.otp
    })

    if not record:
        raise HTTPException(status_code=400, detail="Invalid OTP or email.")

    await users_collection.insert_one({
        "name": record["name"],
        "email": record["email"],
        "password": record["password"]
    })

    await otp_collection.delete_one({"_id": record["_id"]})

    return {"message": "Signup verified successfully. You can now login."}

@router.post("/login")
async def login(user: UserLogin):
    db_user = await users_collection.find_one({"email": user.email.strip().lower()})
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token({"user_id": str(db_user["_id"])})
    return {
        "access_token": token,
        "name": db_user["name"],
        "user_id": str(db_user["_id"])
    }

# ✅ NEW: Fetch current user profile
@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"]
    } 