from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.quizzes.schemas import AttemptQuizSchema

QuestionTitle = str

class CreateAttempt(BaseModel):
    quiz_id: int
    user_id: int
    start_time: datetime
    spent_time: str


class AttemptReturn(BaseModel):
    id: int
    quiz: AttemptQuizSchema
    
    class Config:
        from_attributes = True


class AttemptResult(BaseModel):
    spent_time: str
    result: int


class AttemptQuestionAnswer(BaseModel):
    title: str
    answers: list[str]
    user_answer: Optional[str]
    is_correct: Optional[bool]


class AttemptResultResponseModel(BaseModel):
    quiz: str
    result: str
    spent_time: str
    questions: list[AttemptQuestionAnswer]


class AttemptListResponseModel(BaseModel):
    id: int
    quiz_title: str
    result: str
    spent_time: str
    answers_are_expired: bool 
