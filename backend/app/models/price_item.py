from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, Date, Enum, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class CurrencyEnum(str, enum.Enum):
    KZT = "KZT"
    USD = "USD"
    RUB = "RUB"

class PriceItem(Base):
    __tablename__ = "price_items"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("price_documents.id", ondelete="CASCADE"), nullable=False)
    partner_id = Column(Integer, ForeignKey("partners.id", ondelete="CASCADE"), nullable=False)
    
    service_name_raw = Column(String, nullable=False)
    service_code_source = Column(String, nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    
    price_resident_kzt = Column(Numeric(10, 2), nullable=True)
    price_nonresident_kzt = Column(Numeric(10, 2), nullable=True)
    price_original = Column(Numeric(10, 2), nullable=True)
    currency_original = Column(Enum(CurrencyEnum), default=CurrencyEnum.KZT)
    
    is_verified = Column(Boolean, default=False)
    verification_note = Column(String, nullable=True)
    effective_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    
    match_score = Column(Float, nullable=True)

    document = relationship("PriceDocument", back_populates="price_items")
    service = relationship("Service", back_populates="price_items")
    partner = relationship("Partner")
