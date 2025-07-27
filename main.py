# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure these imports match your project structure
from routes.auth_routes import router as auth_router
from routes.jd_routes import router as jd_router
from routes.ai_routes import router as ai_router
from routes.upload_to_drive import router as drive_upload_router # Your original main.py for drive upload

app = FastAPI(
    title="Resume Shortlister API",
    description="Backend API for login, JD submission, and scoring",
    version="1.0.0"
)

origins = [
    "http://localhost:9002",
    "http://localhost:3000"
    # Add your frontend deployment URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(jd_router)
app.include_router(ai_router)
app.include_router(drive_upload_router) # This router for direct file uploads to Drive

@app.get("/")
def root():
    return {"message": "Login/Signup backend running"}