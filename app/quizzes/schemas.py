import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette import status

from .models import Answear, Question, Quizz

logger = logging.getLogger("main_logger")


class AnswearBaseSchema(BaseModel):
    title: str
    question_id: int

    class Config:
        from_attributes = True


class AnswearSchema(AnswearBaseSchema):
    id: int


class AnswearCreateSchema(AnswearBaseSchema):
    is_correct: bool


class AnswearUpdateSchema(BaseModel):
    title: Optional[str] = None
    is_correct: Optional[bool] = None


class QuestionBaseSchema(BaseModel):
    title: str
    quizz_id: int 

    class Config:
        from_attributes = True


class QuestionSchema(QuestionBaseSchema):
    id: int
    answears: Optional[List[AnswearSchema]] = None
    
    class Config:
        from_attributes = True


class QuestionUpdateSchema(BaseModel):
    title: Optional[str] = None


class QuizzBaseSchema(BaseModel):
    title: str
    description: str
    company_id: int

    class Config:
        from_attributes = True
        from_dict = True


class QuizzSchema(QuizzBaseSchema):
    id: int
    questions: Optional[List[QuestionSchema]] = None


class QuizzUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


    