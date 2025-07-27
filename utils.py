# utils/auth_utils.py
import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi import HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional # Added for Optional type hint

# ✅ Load environment variables
load_dotenv()

# Moved SECRET_KEY to be consistent with previous suggestions for JWT_SECRET
JWT_SECRET = os.getenv("JWT_SECRET") 
ALGORITHM = "HS256"

# Ensure JWT_SECRET is set
if not JWT_SECRET:
    raise ValueError("Environment variable 'JWT_SECRET' not set. Please set it in your .env file.")

# ✅ Hash the password (returns string)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# ✅ Verify a given password with the hashed one
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ✅ Create JWT access token with expiration
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=1) # Default expiry
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

# ✅ Decode JWT token and return payload or raise HTTP error
def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ✅ Send OTP email using Gmail SMTP
async def send_email_otp(to_email: str, otp: str):
    sender_email = os.getenv("SMTP_SENDER_EMAIL")
    sender_password = os.getenv("SMTP_SENDER_PASSWORD")

    if not sender_email or not sender_password:
        raise Exception("❌ SMTP credentials are missing in the .env file")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Verify your email - Resume Shortlister"

    body = f"""
    <h2>Email Verification - OTP</h2>
    <p>Hello,</p>
    <p>Your OTP to verify your email is:</p>
    <h3>{otp}</h3>
    <p>This OTP will expire in 10 minutes.</p>
    """

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
    except Exception as e:
        raise Exception(f"Failed to send OTP email: {str(e)}")