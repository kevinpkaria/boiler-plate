import os
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
engine = create_engine(os.getenv("DATABASE_URL"), echo=True)
SessionLocal = sessionmaker(bind=engine)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    company_id = Column(String, nullable=False, unique=True)
    client_id = Column(String, nullable=False, unique=True)
    auth_code = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    token_type = Column(String)
    expires_at = Column(DateTime)
    scope = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversations = relationship("Conversation", back_populates="company")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"), nullable=False)
    conversation_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="conversations")


# Create tables
Base.metadata.create_all(engine)
