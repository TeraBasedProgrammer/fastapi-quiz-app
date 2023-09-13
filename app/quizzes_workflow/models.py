from datetime import datetime, timedelta

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Text,
                        Time)
from sqlalchemy.orm import relationship

from app.database import Base


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"))
    quiz = relationship("Quiz", back_populates="attempts", lazy='joined')
    user = relationship("User", back_populates="attempts", lazy='joined')
    start_time = Column(DateTime, default=datetime.utcnow())
    end_time = Column(DateTime)
    spent_time = Column(String)
    result = Column(Integer, default=0)
    