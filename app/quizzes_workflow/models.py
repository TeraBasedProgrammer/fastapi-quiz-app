from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Attemp(Base):
    __tablename__ = "attemps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"))
    quiz = relationship("Quiz", back_populates="attemps", lazy='joined')
    user = relationship("User", back_populates="attemps", lazy='joined')
    start_time = Column(DateTime, default=datetime.utcnow())
    end_time = Column(DateTime)
    spent_time = Column(DateTime, nullable=True)
    result = Column(Integer, nullable=True)


    @property
    def set_result(self) -> None:
        # TODO: Use service that counts correct answers using data from Redis
        ...

    @property
    def set_spent_time(self) -> None:
        # TODO: Subtract start time from datetime.utcnow when attemp is over
        ...