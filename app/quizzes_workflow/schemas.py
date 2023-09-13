from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.quizzes.schemas import AttemptQuizSchema


class CreateAttempt(BaseModel):
    quiz_id: int
    user_id: int
    start_time: datetime


class AttemptReturn(BaseModel):
    id: int
    quiz: AttemptQuizSchema
    
    class Config:
        from_attributes = True


class AttemptResult(BaseModel):
    spent_time: str
    result: int
