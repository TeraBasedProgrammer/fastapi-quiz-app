from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow())

