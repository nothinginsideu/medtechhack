from sqlalchemy import Column, Integer, String, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base

class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=True)
    address = Column(String, nullable=True)
    bin = Column(String(12), nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)  # Конфиг для парсинга прайсов

    price_documents = relationship("PriceDocument", back_populates="partner", cascade="all, delete-orphan")
