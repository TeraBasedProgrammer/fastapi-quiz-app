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
    
    users = relationship("User", secondary="company_user", back_populates="companies") 
    user_association = relationship("CompanyUser", back_populates="company")



class CompanyUser(Base): 
    __tablename__ = "company_user"
    company_id = Column(ForeignKey('companies.id', ondelete="CASCADE"), primary_key=True)
    user_id = Column(ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    role = Column(Enum(RoleEnum), nullable=False)

    user = relationship("User", back_populates="company_association") 
    company = relationship("Company",  back_populates="user_association")

    # # proxies
    # user_email = association_proxy(target_collection='user', attr='email')
    # company_title = association_proxy(target_collection='company', attr='title')
