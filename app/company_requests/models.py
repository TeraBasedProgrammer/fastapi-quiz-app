from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint

from app.database import Base


class CompanyRequest(Base):
    __tablename__ = "company_request"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    receiver_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    company_id = Column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
         UniqueConstraint("sender_id", "receiver_id", "company_id", name="_company_request_uc"),
         )