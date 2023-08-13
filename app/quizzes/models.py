from sqlalchemy import (Boolean, Column, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database import Base


class Quizz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    company_id = Column(ForeignKey("companies.id", ondelete="CASCADE"))
    fully_created = Column(Boolean, nullable=False, default=False)
    # daily_attemps - ?

    questions = relationship("Question", back_populates="quizz", lazy='subquery') 

    __table_args__ = (
         UniqueConstraint("title", "company_id", name="_quizz_uc"),
         )
    
   
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    quizz_id = Column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    fully_created = Column(Boolean, nullable=False, default=False)

    quizz = relationship("Quizz", back_populates="questions", lazy='subquery')
    answears = relationship("Answear", back_populates="question", lazy='subquery')

    __table_args__ = (
         UniqueConstraint("title", "quizz_id", name="_question_uc"),
         )
    

class Answear(Base):
    __tablename__ = "answears"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    question_id = Column(ForeignKey("questions.id", ondelete="CASCADE"))

    question = relationship("Question", back_populates="answears", lazy='subquery')

    __table_args__ = (
         UniqueConstraint("title", "question_id", name="_answear_uc"),
         )