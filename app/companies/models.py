from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String

from app.database import Base


class User(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # email = Column(String, nullable=False, unique=True)
    # name = Column(String, nullable=True)
    # registered_at = Column(TIMESTAMP, default=datetime.utcnow)
    # password = Column(String(length=1024), nullable=False)
    # auth0_registered = Column(Boolean, default=False, nullable=False)

