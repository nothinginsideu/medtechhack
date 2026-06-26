from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Date, Text
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime
import enum

class ParseStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"
    needs_review = "needs_review"

class FileFormat(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    xlsx = "xlsx"
    scan_pdf = "scan_pdf"

class PriceDocument(Base):
    __tablename__ = "price_documents"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String, nullable=False)
    file_format = Column(Enum(FileFormat), nullable=False)
    effective_date = Column(Date, nullable=True)
    
    parsed_at = Column(DateTime, nullable=True)
    parse_status = Column(Enum(ParseStatus), default=ParseStatus.pending)
    parse_log = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    
    partner = relationship("Partner", back_populates="price_documents")
    price_items = relationship("PriceItem", back_populates="document", cascade="all, delete-orphan")
