from pydantic import BaseModel, EmailStr

class UserSignupInit(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserVerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str