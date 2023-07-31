from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CompanyRequest(Base):
    __tablename__ = "company_request"
    __table_args__ = (UniqueConstraint("sender_id", "receiver_id", "company_id", name="_company_request_uc"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # Add relationship fields