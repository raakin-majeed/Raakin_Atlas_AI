from pydantic import BaseModel
from typing import Dict


class StudentProfileCreate(BaseModel):
    user_id: int
    attendance_percentage: float
    subject_scores: Dict[str, float]


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    attendance_percentage: float
    subject_scores: Dict[str, float]

    class Config:
        from_attributes = True