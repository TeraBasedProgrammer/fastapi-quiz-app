import enum
from datetime import datetime

from sqlalchemy import (DECIMAL, TIMESTAMP, Boolean, Column, Enum, ForeignKey,
                        Integer, String)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(enum.Enum):
    Owner = "owner"
    Admin = "admin"
    Member = "member"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow())
    
    users = relationship("CompanyUser", back_populates="companies") 

    def __repr__(self) -> str:
        return f"Company {self.title}"


class CompanyUser(Base): 
    __tablename__ = "company_user"
    company_id = Column(ForeignKey('companies.id', ondelete="CASCADE"), primary_key=True)
    user_id = Column(ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.Member)
    average_score = Column(DECIMAL, default=0)

    users = relationship("User", back_populates="companies", lazy='subquery') 
    companies = relationship("Company",  back_populates="users", lazy='subquery')
