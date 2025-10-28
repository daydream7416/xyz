from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    properties = relationship("Property", back_populates="owner", cascade="all, delete-orphan")
    agent = relationship("Agent", back_populates="users")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    company = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    profile_photo_url = Column(String, nullable=True)
    city = Column(String, nullable=True)
    happy_customers = Column(Integer, nullable=True)
    successful_sales = Column(Integer, nullable=True)
    instagram_url = Column(String, nullable=True)
    facebook_url = Column(String, nullable=True)
    slug = Column(String, unique=True, index=True)
    is_premium = Column(Boolean, default=False, nullable=False)
    users = relationship("User", back_populates="agent")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    tagline = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    area = Column(String, nullable=True)
    rooms = Column(String, nullable=True)
    zoning_status = Column(String, nullable=True)
    floor = Column(String, nullable=True)
    building_age = Column(String, nullable=True)
    specs = Column(Text, nullable=True)
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="properties")
