from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base

class Partner(Base):
    __tablename__ = "partners"

    id = Column("partner_id", Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=True)
    address = Column(String, nullable=True)
    bin = Column(String(12), nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_date = Column(DateTime, nullable=True)
    config = Column(JSON, nullable=True)  # Конфиг для парсинга прайсов

    price_documents = relationship("PriceDocument", back_populates="partner", cascade="all, delete-orphan")
