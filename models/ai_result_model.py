from pydantic import BaseModel
from typing import Optional

class AIResult(BaseModel):
    jd_id: str
    name: str  
    skills_score: float  # 0–70
    jd_score: float      # 0–1
    description: Optional[str] = None
    overall_score: Optional[float] = None  # Computed in backend
