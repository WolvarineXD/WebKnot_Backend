from pydantic import BaseModel  ,HttpUrl
from typing import Dict, Optional ,List 

class JDInput(BaseModel):
    job_title: str
    job_description: str
    skills: Dict[str, int]
    resume_drive_links: Optional[List[HttpUrl]] = None
