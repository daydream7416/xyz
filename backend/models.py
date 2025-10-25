from sqlalchemy import Column, Integer, String, Float
from .database import Base

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