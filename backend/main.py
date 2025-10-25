from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import Agent

class AgentCreate(BaseModel):
    name: str
    email: str
    phone: str
    company: str
    experience: str
    profile_photo_url: str
    city: str
    happy_customers: int
    successful_sales: int
    instagram_url: str
    facebook_url: str
    slug: str

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/agents/")
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    db_agent = Agent(**agent.dict())
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent