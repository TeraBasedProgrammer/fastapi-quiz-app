import logging
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.utils import validate_text

logger = logging.getLogger("main_logger")


class AnswerBaseSchema(BaseModel):
    title: str
    question_id: int

    @field_validator("title")
    def validate_title(cls, value):
        return validate_text(value)

    class Config:
        from_attributes = True


class AnswerSchema(AnswerBaseSchema):
    id: int
    is_correct: bool


class AnswerCreateSchema(AnswerBaseSchema):
    is_correct: bool


class AnswerUpdateSchema(BaseModel):
    title: Optional[str] = None
    is_correct: Optional[bool] = None
 
    @field_validator("title")
    def validate_title(cls, value):
        return validate_text(value)
    

class QuestionBaseSchema(BaseModel):
    title: str
    quiz_id: int 

    @field_validator("title")
    def validate_title(cls, value):
        return validate_text(value)

    class Config:
        from_attributes = True


class QuestionSchema(QuestionBaseSchema):
    id: int
    answers: Optional[List[AnswerSchema]] = None
    
    class Config:
        from_attributes = True


class QuestionUpdateSchema(BaseModel):
    title: Optional[str] = None


class QuizBaseSchema(BaseModel):
    title: str
    description: str
    company_id: int
    completion_time: int 

    @field_validator("title")
    def validate_title(cls, value):
        return validate_text(value)

    class Config:
        from_attributes = True
        from_dict = True


class QuizSchema(QuizBaseSchema):
    id: int
    questions: Optional[List[QuestionSchema]] = None


class QuizListSchema(BaseModel):
    id: int
    title: str
    description: str
    completion_time: int
    questions_count: int

    class Config:
        from_attributes = True

class QuizUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completion_time: Optional[int] = None

    @field_validator("title")
    def validate_title(cls, value):
        return validate_text(value)


class UpdateModelStatus(BaseModel):
    fully_created: bool


class AttempAnswerSchema(AnswerBaseSchema):
    id: int


class AttempQuestionSchema(QuestionBaseSchema):
    id: int
    answers: List[AttempAnswerSchema]
    
    class Config:
        from_attributes = True

class AttempQuizSchema(QuizBaseSchema):
    id: int
    completion_time: int
    questions_count: int
    questions: List[AttempQuestionSchema]
    



    