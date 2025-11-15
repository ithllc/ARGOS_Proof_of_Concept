from pydantic import BaseModel
from typing import List, Optional, Dict

class Task(BaseModel):
    task_id: str
    type: str
    paper_url: Optional[str] = None
    params: Optional[Dict] = {}

class AgentStatus(BaseModel):
    agent_id: str
    status: str # e.g., "IDLE", "BUSY", "ERROR"
    current_task: Optional[str] = None

class PaperAnalysisResult(BaseModel):
    paper_id: str
    title: str
    summary: str
    concepts: List[str]
    methodology: str
