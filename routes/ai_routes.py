from fastapi import APIRouter, HTTPException, Security, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.ai_result_model import AIResult
from db import ai_results_collection
from utils import decode_access_token
from bson import ObjectId
from bson.errors import InvalidId
from typing import List

router = APIRouter(prefix="/ai", tags=["AI Results"])
security = HTTPBearer()

@router.post("/store")
async def store_bulk_ai_results(
    results: List[AIResult],
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    try:
        docs = []
        for result in results:
            overall_score = (result.jd_score * 30) + result.skills_score

            doc = {
                "jd_id": ObjectId(result.jd_id),
                "user_id": ObjectId(user_id),
                "name": result.name,  # ✅ name
                "skills_score": result.skills_score,
                "jd_score": result.jd_score,
                "description": result.description,
                "overall_score": round(overall_score, 2)
            }
            docs.append(doc)

        await ai_results_collection.insert_many(docs)

        return {"message": f"{len(docs)} AI results stored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store AI results: {str(e)}")

@router.get("/results/{jd_id}")
async def get_ai_results_for_jd(
    jd_id: str = Path(..., description="JD ID to fetch AI results for"),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    try:
        cursor = ai_results_collection.find({
            "jd_id": ObjectId(jd_id),
            "user_id": ObjectId(user_id)
        })

        results = []
        async for doc in cursor:
            results.append({
                "name": doc["name"],
                "skills_score": doc["skills_score"],
                "jd_score": doc["jd_score"],
                "overall_score": doc["overall_score"],
                "description": doc.get("description")
            })

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI results: {str(e)}")

@router.get("/candidate-count/{jd_id}")
async def get_candidate_count(
    jd_id: str = Path(..., description="JD ID to fetch candidate count for"),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    try:
        query = {
            "jd_id": ObjectId(jd_id),
            "user_id": ObjectId(user_id)
        }
        count = await ai_results_collection.count_documents(query)
        return {"count": count}

    except InvalidId:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid jd_id or user_id format. Got jd_id='{jd_id}' and user_id='{user_id}'."
        )
    except Exception as e:
        print(f"Error in candidate-count endpoint: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )
