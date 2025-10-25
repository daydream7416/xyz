from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, declarative_base
from pydantic import BaseModel

from database import engine, get_db
from models import Agent

# SQLAlchemy Base
Base = declarative_base()

# Pydantic model for creating an agent
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

# Pydantic model for reading an agent
class AgentRead(AgentCreate):
    id: int

    class Config:
        orm_mode = True

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/agents/", response_model=AgentRead)
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    db_agent = Agent(**agent.dict())
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@app.get("/agents/", response_model=list[AgentRead])
def read_agents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    agents = db.query(Agent).offset(skip).limit(limit).all()
    return agents

@app.get("/agents/{slug}", response_model=AgentRead)
def read_agent(slug: str, db: Session = Depends(get_db)):
    db_agent = db.query(Agent).filter(Agent.slug == slug).first()
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@app.put("/agents/{slug}", response_model=AgentRead)
def update_agent(slug: str, agent: AgentCreate, db: Session = Depends(get_db)):
    db_agent = db.query(Agent).filter(Agent.slug == slug).first()
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    for var, value in vars(agent).items():
        setattr(db_agent, var, value) if value else None

    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@app.delete("/agents/{slug}")
def delete_agent(slug: str, db: Session = Depends(get_db)):
    db_agent = db.query(Agent).filter(Agent.slug == slug).first()
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(db_agent)
    db.commit()
    return {"message": "Agent deleted successfully"}