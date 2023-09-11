from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String, DECIMAL
from sqlalchemy.orm import relationship

from app.database import Base
from app.quizzes_workflow.models import Attemp


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    registered_at = Column(TIMESTAMP, default=datetime.utcnow())
    password = Column(String(length=1024), nullable=False)
    auth0_registered = Column(Boolean, default=False, nullable=False)
    overall_avg_score = Column(DECIMAL, default=0)

    companies = relationship("CompanyUser", back_populates="users")
    attemps = relationship("Attemp", back_populates="user", lazy='joined') 

    def __repr__(self):
        return f"User {self.email}"
