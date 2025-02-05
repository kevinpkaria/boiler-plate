from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///fynd_oauth.db", echo=True)
SessionLocal = sessionmaker(bind=engine)


class MerchantToken(Base):
    __tablename__ = "merchant_tokens"

    id = Column(Integer, primary_key=True)
    company_id = Column(String, nullable=False)
    client_id = Column(String, nullable=False, unique=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_type = Column(String)
    expires_at = Column(DateTime)
    scope = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StateStore(Base):
    __tablename__ = "state_store"

    id = Column(Integer, primary_key=True)
    state = Column(String, nullable=False)
    company_id = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    auth_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(engine)
