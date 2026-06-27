from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base

class Service(Base):
    """
    Эталонный справочник услуг.
    """
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    specialty = Column(String, index=True, nullable=True)
    code = Column(String, index=True, nullable=True)
    category = Column(String, index=True, nullable=True)
    icd_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    name_ru = Column(String, index=True, nullable=False)
    tarificator_code = Column(String, nullable=True)
    synonyms = Column(JSON, nullable=True)

    # Связь с конкретными ценами клиник (1 ко многим)
    price_items = relationship("PriceItem", back_populates="service")
