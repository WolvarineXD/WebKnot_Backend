from fastapi import APIRouter, HTTPException, Security, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.jd_model import JDInput # Ensure this is the updated model
from utils import decode_access_token
from db import jd_collection
from datetime import datetime
from bson import ObjectId
import httpx
from typing import Dict, Any, List # Added for consistent type hinting
from pydantic import HttpUrl # <--- IMPORTANT: Ensure HttpUrl is imported if used in JDInput

router = APIRouter(prefix="/jd", tags=["JD"])
security = HTTPBearer()

# 👇 Replace this with your actual deployed AI endpoint if needed
AI_ENDPOINT = "http://localhost:5678/webhook-test/b2d90787-cbb4-448c-93c5-6a31eacfa99a"


async def notify_ai(jd_id: str, jd_data: JDInput, token: str):
    try:
        # --- START OF CHANGE IN notify_ai ---
        # Prepare resume_drive_links for JSON serialization
        # Convert HttpUrl objects to strings
        serialized_resume_links: List[str] = []
        if jd_data.resume_drive_links:
            serialized_resume_links = [str(link) for link in jd_data.resume_drive_links]
        # --- END OF CHANGE IN notify_ai ---

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                AI_ENDPOINT,
                json={
                    "jd_id": jd_id,
                    "job_title": jd_data.job_title,
                    "job_description": jd_data.job_description,
                    "skills": jd_data.skills,
                    # ✅ Use the serialized list of links
                    "resume_drive_links": serialized_resume_links 
                },
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            print(f"📨 AI Response {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Failed to send JD to AI: {e}")


# ✅ Submit JD
@router.post("/submit")
async def submit_jd(
    jd: JDInput,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = credentials.credentials
    user_id = decode_access_token(token).get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Convert jd_data to a dictionary, ensuring HttpUrl objects become strings for MongoDB
    jd_doc: Dict[str, Any] = jd.model_dump(mode='json') 
    
    # Override/add fields for MongoDB
    jd_doc["user_id"] = ObjectId(user_id)
    jd_doc["created_at"] = datetime.utcnow()

    # The `jd.model_dump(mode='json')` should already convert HttpUrl to str,
    # but this ensures that `resume_drive_links` is always a list of strings for MongoDB.
    if jd_doc.get("resume_drive_links") is None:
        jd_doc["resume_drive_links"] = [] 

    result = await jd_collection.insert_one(jd_doc)
    jd_id = str(result.inserted_id)

    # Call notify_ai with the original JDInput object, as it expects HttpUrl
    await notify_ai(jd_id, jd, token) # Pass the original jd object (JDInput type)

    return {"message": "JD submitted and sent to AI", "jd_id": jd_id}


# ✅ Update JD
@router.put("/update/{jd_id}")
async def update_jd(
    jd_id: str,
    updated_data: JDInput, # This uses the updated JDInput
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = credentials.credentials
    user_id = decode_access_token(token).get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Convert updated_data to a dictionary, ensuring HttpUrl objects become strings for MongoDB
    update_doc: Dict[str, Any] = updated_data.model_dump(mode='json')

    if update_doc.get("resume_drive_links") is None:
        update_doc["resume_drive_links"] = [] 

    result = await jd_collection.update_one(
        {
            "_id": ObjectId(jd_id),
            "user_id": ObjectId(user_id)
        },
        {
            "$set": {
                "job_title": update_doc["job_title"],
                "job_description": update_doc["job_description"],
                "skills": update_doc["skills"],
                "resume_drive_links": update_doc["resume_drive_links"], 
                "created_at": datetime.utcnow() # Consider using 'updated_at' here
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="JD not found or no changes made")

    from db import ai_results_collection
    await ai_results_collection.delete_many({"jd_id": ObjectId(jd_id)})

    # Call notify_ai with the original JDInput object, as it expects HttpUrl
    await notify_ai(jd_id, updated_data, token) # Pass the original updated_data object (JDInput type)

    return {"message": "JD updated and sent to AI", "jd_id": jd_id}


# ✅ Get JD History (sorted by most recent)
@router.get("/history")
async def get_jd_history(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    user_id = decode_access_token(token).get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    history = []
    cursor = jd_collection.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
    
    async for jd in cursor:
        parsed_skills = {}
        for skill, weight in jd.get("skills", {}).items():
            if isinstance(weight, dict) and "$numberInt" in weight:
                parsed_skills[skill] = int(weight["$numberInt"])
            else:
                parsed_skills[skill] = weight

        history.append({
            "jd_id": str(jd["_id"]),
            "job_title": jd["job_title"],
            "job_description": jd["job_description"],
            "skills": parsed_skills,
            "resume_drive_links": jd.get("resume_drive_links", []), 
            "created_at": jd.get("created_at")
        })

    return {"history": history}


# ✅ Delete JD
@router.delete("/delete/{jd_id}")
async def delete_jd(
    jd_id: str = Path(..., description="JD ID to delete"),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = credentials.credentials
    user_id = decode_access_token(token).get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await jd_collection.delete_one({
        "_id": ObjectId(jd_id),
        "user_id": ObjectId(user_id)
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="JD not found")

    return {"message": "JD deleted successfully"}