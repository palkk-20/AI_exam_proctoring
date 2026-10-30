from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CandidateRegisterRequest(BaseModel):
    name: str
    roll_no: str
    email: Optional[str] = ""

class ViolationReportRequest(BaseModel):
    session_id: str
    violation_type: str
    description: str
    severity: Optional[str] = "MEDIUM"
    snapshot_base64: Optional[str] = None

class ExamSubmitRequest(BaseModel):
    session_id: str
    answers: Dict[str, int] # question_id (as str) -> selected_option_index

class AdminActionRequest(BaseModel):
    action: str # "WARNING", "TERMINATE", "CLEAR"
    message: Optional[str] = None

class QuestionCreateRequest(BaseModel):
    question_text: str
    options: List[str]
    correct_index: int = 0
    category: Optional[str] = "General"
