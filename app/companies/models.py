import enum
from datetime import datetime

from sqlalchemy import (TIMESTAMP, Boolean, Column, Enum, ForeignKey, Integer,
                        String)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow())
    
    users = relationship("CompanyUser", back_populates="companies") 


class CompanyUser(Base): 
    __tablename__ = "company_user"
    company_id = Column(ForeignKey('companies.id', ondelete="CASCADE"), primary_key=True)
    user_id = Column(ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.member)

    users = relationship("User", back_populates="companies", lazy='subquery') 
    companies = relationship("Company",  back_populates="users", lazy='subquery')
