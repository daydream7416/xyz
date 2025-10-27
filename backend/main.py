from fastapi import FastAPI, Depends, HTTPException, Form, File, UploadFile, Request
from sqlalchemy.orm import Session, declarative_base
from pydantic import BaseModel
import os
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import httpx
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse, urlunparse

from database import engine, get_db
from models import Agent

# Load environment variables from .env file
load_dotenv()
local_env_path = Path(__file__).resolve().parent / ".env.local"
if local_env_path.exists():
    load_dotenv(local_env_path, override=True)

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

# Pydantic model for reading an agent - allows optional fields
class AgentRead(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    company: str
    experience: str
    profile_photo_url: str | None = None
    city: str
    happy_customers: int
    successful_sales: int
    instagram_url: str | None = None
    facebook_url: str | None = None
    slug: str

    class Config:
        orm_mode = True

# Create database tables
Base.metadata.create_all(bind=engine)

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)
CLOUDINARY_CONFIGURED = all([
    os.getenv("CLOUDINARY_CLOUD_NAME"),
    os.getenv("CLOUDINARY_API_KEY"),
    os.getenv("CLOUDINARY_API_SECRET")
])

# Create FastAPI app
app = FastAPI()

# Configure CORS middleware - EN ÖNEMLİ: Endpoint'lerden önce tanımlanmalı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "*"],  # Local frontend için izin ver
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],  # Tüm header'ları expose et
    max_age=3600,  # Preflight cache süresi
)

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

# CORS preflight için OPTIONS handler
@app.options("/api/register")
async def options_register():
    return {"message": "OK"}

# CORS preflight için OPTIONS handler - /api/agent/register için
@app.options("/api/agent/register")
async def options_agent_register():
    return {"message": "OK"}

def _extract_base_url(header_value: str | None) -> str | None:
    if not header_value:
        return None
    parsed = urlparse(header_value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return None


def resolve_frontend_base_url(request: Request) -> str:
    override = os.getenv("FRONTEND_BASE_URL")
    if override:
        return override.rstrip("/")

    for header_name in ("origin", "referer"):
        candidate = _extract_base_url(request.headers.get(header_name))
        if candidate:
            return candidate

    host = request.headers.get("host")
    if host:
        return f"{request.url.scheme}://{host}".rstrip("/")

    return "https://metra-ai-monorepo.vercel.app"


def build_landing_page_url(frontend_base_url: str, slug: str) -> str:
    base = (frontend_base_url or "").rstrip("/")
    if not base:
        return f"/landing/main.html?agent={slug}"
    return f"{base}/landing/main.html?agent={slug}"


def build_agent_subdomain_url(frontend_base_url: str, slug: str) -> str | None:
    """Derive https://{slug}.example.com if wildcard subdomain setup exists."""
    if not frontend_base_url or not slug:
        return None

    parsed = urlparse(frontend_base_url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc
    if not host:
        return None

    host_no_port, _, port = host.partition(":")
    if host_no_port.startswith("www."):
        host_no_port = host_no_port[4:]

    # Yalnızca özel domainlerde subdomain üretelim (localhost veya vercel app değil)
    invalid_hosts = {"localhost", "127.0.0.1"}
    if not host_no_port or any(host_no_port.startswith(prefix) for prefix in invalid_hosts) or host_no_port.endswith(".vercel.app"):
        return None

    netloc = f"{slug}.{host_no_port}"
    if port:
        netloc = f"{netloc}:{port}"

    return urlunparse((scheme, netloc, "", "", "", ""))


@app.post("/api/register")
async def register_agent_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    company: str = Form(...),
    experience: str = Form(...),
    city: str = Form(...),
    happy_customers: str = Form(...),
    successful_sales: str = Form(...),
    instagram_url: str = Form(""),
    facebook_url: str = Form(""),
    slug: str = Form(""),
    profilePhoto: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Initialize image_url as None
    image_url = None
    
    # If profile photo is uploaded, upload to Cloudinary
    if profilePhoto:
        if CLOUDINARY_CONFIGURED:
            try:
                upload_result = cloudinary.uploader.upload(profilePhoto.file)
                image_url = upload_result.get("secure_url", "")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")
        else:
            print("Cloudinary not configured; skipping profile photo upload for local testing.")
    
    # Convert string numbers to integers
    try:
        happy_customers_int = int(happy_customers)
        successful_sales_int = int(successful_sales)
    except ValueError:
        raise HTTPException(status_code=400, detail="happy_customers and successful_sales must be valid numbers")
    
    # Auto-generate slug if not provided
    if not slug:
        import re
        # Türkçe karakterleri İngilizce karşılıkları ile değiştir
        tr_chars = {'ç':'c', 'ğ':'g', 'ı':'i', 'İ':'i', 'ö':'o', 'ş':'s', 'ü':'u', 'Ç':'c', 'Ğ':'g', 'Ö':'o', 'Ş':'s', 'Ü':'u'}
        clean_name = name
        for tr_char, en_char in tr_chars.items():
            clean_name = clean_name.replace(tr_char, en_char)
        
        slug = re.sub(r'[^\w\s-]', '', clean_name).strip().lower()
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Eğer aynı slug varsa, benzersiz olması için sayı ekle
        existing_agent = db.query(Agent).filter(Agent.slug == slug).first()
        if existing_agent:
            count = 1
            while existing_agent:
                new_slug = f"{slug}-{count}"
                existing_agent = db.query(Agent).filter(Agent.slug == new_slug).first()
                count += 1
            slug = new_slug
    
    # Prevent duplicate email registrations
    existing_email_agent = db.query(Agent).filter(Agent.email == email).first()
    if existing_email_agent:
        raise HTTPException(
            status_code=400,
            detail="Bu e-posta adresiyle daha önce kayıt yapılmış. Lütfen farklı bir e-posta deneyin."
        )

    # Ensure slug is unique even if provided manually
    existing_slug_agent = db.query(Agent).filter(Agent.slug == slug).first()
    if existing_slug_agent:
        raise HTTPException(
            status_code=400,
            detail="Bu isimle daha önce kayıt yapılmış. Lütfen farklı bir isim/slug seçin."
        )

    # Create new agent with form data and uploaded image URL
    new_agent = Agent(
        name=name,
        email=email,
        phone=phone,
        company=company,
        experience=experience,
        profile_photo_url=image_url,  # Cloudinary'den gelen URL
        city=city,
        happy_customers=happy_customers_int,
        successful_sales=successful_sales_int,
        instagram_url=instagram_url,
        facebook_url=facebook_url,
        slug=slug
    )
    
    # Save to database
    db.add(new_agent)
    db.commit()
    frontend_base_url = resolve_frontend_base_url(request)
    landing_url = build_landing_page_url(frontend_base_url, new_agent.slug)
    agent_url = build_agent_subdomain_url(frontend_base_url, new_agent.slug)

    db.refresh(new_agent)
    
    # Send webhook to n8n after successful database save
    n8n_webhook_url = os.getenv("N8N_TELEGRAM_WEBHOOK_URL")
    if n8n_webhook_url:
        webhook_payload = {
            "message": "Yeni emlakçı kaydı!",
            "agent": {
                "id": new_agent.id,
                "name": new_agent.name,
                "email": new_agent.email,
                "phone": new_agent.phone,
                "company": new_agent.company,
                "experience": new_agent.experience,
                "city": new_agent.city,
                "happy_customers": new_agent.happy_customers,
                "successful_sales": new_agent.successful_sales,
                "instagram_url": new_agent.instagram_url,
                "facebook_url": new_agent.facebook_url,
                "profile_photo_url": new_agent.profile_photo_url,
                "slug": new_agent.slug,
                "landing_url": landing_url,
                "agent_url": agent_url or landing_url
            }
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(n8n_webhook_url, json=webhook_payload)
        except httpx.RequestError as e:
            print(f"Uyarı: n8n webhook tetiklenemedi: {e}")
        except Exception as e:
            print(f"Uyarı: n8n webhook beklenmeyen hata: {e}")

    return {
        "message": "Agent registered successfully",
        "agent_id": new_agent.id,
        "name": new_agent.name,
        "email": new_agent.email,
        "profile_photo_url": new_agent.profile_photo_url,
        "slug": new_agent.slug,
        "landing_url": landing_url,
        "agent_url": agent_url or landing_url
    }

# /api/agent/register endpoint - /api/register ile aynı işlevi yapar
@app.post("/api/agent/register")
async def register_agent_form_v2(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    company: str = Form(...),
    experience: str = Form(...),
    city: str = Form(...),
    happy_customers: str = Form(...),
    successful_sales: str = Form(...),
    instagram_url: str = Form(""),
    facebook_url: str = Form(""),
    slug: str = Form(""),
    profilePhoto: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Aynı kodu tekrar kullan
        return await register_agent_form(
            request=request,
            name=name,
            email=email,
            phone=phone,
            company=company,
            experience=experience,
            city=city,
            happy_customers=happy_customers,
            successful_sales=successful_sales,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            slug=slug,
            profilePhoto=profilePhoto,
            db=db
        )
    except Exception as e:
        import traceback
        error_msg = f"Error in register_agent_form_v2: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Console'a yazdır
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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

@app.get("/agents/slug/{slug}", response_model=AgentRead)
def read_agent_by_slug(slug: str, db: Session = Depends(get_db)):
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
