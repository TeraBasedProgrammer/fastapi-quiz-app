from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.quizzes.schemas import AttempQuizSchema


class CreateAttemp(BaseModel):
    quiz_id: int
    user_id: int
    start_time: datetime = datetime.utcnow()


class AttempReturn(BaseModel):
    id: int
    quiz: AttempQuizSchema
    
    class Config:
        from_attributes = True


class AttempResult(BaseModel):
    spent_time: str
    result: int
