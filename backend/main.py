from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Form, File, UploadFile, Request, Header
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import httpx
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse, urlunparse

from database import engine, get_db, Base
from models import Agent, Property, User

# Load environment variables from .env file
load_dotenv()
local_env_path = Path(__file__).resolve().parent / ".env.local"
if local_env_path.exists():
    load_dotenv(local_env_path, override=True)

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
    is_premium: bool = False

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
    is_premium: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    company: str | None = None


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    agent_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PropertyBase(BaseModel):
    title: str
    status: str
    category: str
    price: str | None = None
    location: str | None = None
    description: str | None = None
    tagline: str | None = None
    image_url: str | None = None
    area: str | None = None
    rooms: str | None = None
    zoning_status: str | None = None
    floor: str | None = None
    building_age: str | None = None
    featured: bool = False
    specs: List[str] | None = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    price: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    image_url: Optional[str] = None
    area: Optional[str] = None
    rooms: Optional[str] = None
    zoning_status: Optional[str] = None
    floor: Optional[str] = None
    building_age: Optional[str] = None
    featured: Optional[bool] = None
    specs: Optional[List[str]] = None


class PropertyRead(PropertyBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    specs: List[str] = []
    model_config = ConfigDict(from_attributes=True)

# Create database tables
Base.metadata.create_all(bind=engine)

try:
    SESSION_TTL = timedelta(hours=int(os.getenv("SESSION_TTL_HOURS", "8")))
except ValueError:
    SESSION_TTL = timedelta(hours=8)
ACTIVE_SESSIONS: dict[str, dict[str, datetime]] = {}
ALLOWED_PROPERTY_CATEGORIES = {"arsa", "isyeri", "daire"}


def hash_password(password: str, *, salt: str | None = None) -> str:
    if not password:
        raise HTTPException(status_code=400, detail="Şifre boş olamaz.")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(candidate: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False
    recalculated = hash_password(candidate, salt=salt)
    return secrets.compare_digest(recalculated, stored_hash)


def encode_specs(specs: Optional[List[str]]) -> str | None:
    if not specs:
        return None
    cleaned = [item.strip() for item in specs if item and item.strip()]
    if not cleaned:
        return None
    return json.dumps(cleaned, ensure_ascii=False)


def decode_specs(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def serialize_property(record: Property) -> PropertyRead:
    return PropertyRead(
        id=record.id,
        user_id=record.user_id,
        title=record.title,
        status=record.status,
        category=record.category,
        price=record.price,
        location=record.location,
        description=record.description,
        tagline=record.tagline,
        image_url=record.image_url,
        area=record.area,
        rooms=record.rooms,
        zoning_status=record.zoning_status,
        floor=record.floor,
        building_age=record.building_age,
        featured=record.featured,
        specs=decode_specs(record.specs),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def cleanup_expired_sessions() -> None:
    if not ACTIVE_SESSIONS:
        return
    now = datetime.now(timezone.utc)
    expired_tokens = [token for token, payload in ACTIVE_SESSIONS.items() if payload["expires_at"] <= now]
    for token in expired_tokens:
        ACTIVE_SESSIONS.pop(token, None)


def create_session(user_id: int) -> str:
    cleanup_expired_sessions()
    token = secrets.token_urlsafe(32)
    ACTIVE_SESSIONS[token] = {
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + SESSION_TTL,
    }
    return token


def resolve_session(token: str) -> dict[str, datetime]:
    cleanup_expired_sessions()
    payload = ACTIVE_SESSIONS.get(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş oturum anahtarı.")
    return payload


def require_session(
    token: str = Header(..., alias="X-Session-Token"),
    db: Session = Depends(get_db),
) -> User:
    payload = resolve_session(token)
    user = db.get(User, payload["user_id"])
    if not user or not user.is_active:
        ACTIVE_SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Oturum sahibi bulunamadı veya pasif durumda.")
    return user


def optional_session(
    token: str | None = Header(default=None, alias="X-Session-Token"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return require_session(token=token, db=db)  # type: ignore[arg-type]
    except HTTPException:
        return None


def invalidate_session(token: str) -> None:
    ACTIVE_SESSIONS.pop(token, None)

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
app.state.active_sessions = ACTIVE_SESSIONS

# Configure CORS middleware - EN ÖNEMLİ: Endpoint'lerden önce tanımlanmalı
ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "https://metraai.xyz",
    "https://www.metraai.xyz",
    "https://metraap.com",
    "https://www.metraap.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://([a-z0-9-]+\.)?(metraai\.xyz|metraap\.com)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/agents/", response_model=AgentRead)
def create_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    db_agent = Agent(**agent.model_dump())
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@app.post("/auth/register", response_model=UserRead, tags=["auth"])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Şifre en az 8 karakter olmalı.")
    normalized_email = user.email.lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu e-posta ile zaten bir kullanıcı kayıtlı.")

    agent = db.query(Agent).filter(Agent.email == normalized_email).first()
    if not agent or not agent.is_premium:
        raise HTTPException(status_code=403, detail="Bu danışman için premium yetkisi bulunmuyor.")

    new_user = User(
        name=user.name,
        email=normalized_email,
        hashed_password=hash_password(user.password),
        phone=user.phone,
        company=user.company,
        agent_id=agent.id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login_user(email: EmailStr = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    normalized_email = email.lower()
    db_user = db.query(User).filter(User.email == normalized_email).first()
    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Geçersiz e-posta veya şifre.")

    if not db_user.agent_id:
        raise HTTPException(status_code=403, detail="Premium yetkiniz bulunmuyor.")
    agent = db.get(Agent, db_user.agent_id)
    if not agent or not agent.is_premium:
        raise HTTPException(status_code=403, detail="Premium yetkiniz bulunmuyor.")

    token = create_session(db_user.id)
    return LoginResponse(access_token=token, user=UserRead.model_validate(db_user))


@app.post("/auth/logout", tags=["auth"])
def logout_user(token: str = Header(..., alias="X-Session-Token")):
    invalidate_session(token)
    return {"detail": "Oturum sonlandırıldı."}


@app.get("/auth/me", response_model=UserRead, tags=["auth"])
def read_current_user(current_user: User = Depends(require_session)):
    return current_user


@app.get("/properties/", response_model=List[PropertyRead], tags=["properties"])
def list_properties(
    category: Optional[str] = None,
    status: Optional[str] = None,
    featured: Optional[bool] = None,
    agent_slug: Optional[str] = None,
    agent_email: Optional[str] = None,
    only_mine: bool = False,
    current_user: Optional[User] = Depends(optional_session),
    db: Session = Depends(get_db),
):
    query = db.query(Property)
    joined_agent = False
    if category:
        normalized_category = category.lower()
        if normalized_category not in ALLOWED_PROPERTY_CATEGORIES:
            raise HTTPException(status_code=400, detail="Kategori arsa, isyeri veya daire olmalıdır.")
        query = query.filter(Property.category == normalized_category)
    if status:
        query = query.filter(Property.status == status.lower())
    if featured is not None:
        query = query.filter(Property.featured == featured)
    if agent_slug or agent_email:
        query = query.join(User, Property.user_id == User.id).join(Agent, User.agent_id == Agent.id)
        joined_agent = True
        if agent_slug:
            query = query.filter(Agent.slug == agent_slug)
        if agent_email:
            query = query.filter(Agent.email == agent_email.lower())
    if only_mine:
        if not current_user:
            raise HTTPException(status_code=401, detail="Kendi portföyünüzü görmek için giriş yapmalısınız.")
        query = query.filter(Property.user_id == current_user.id)
        if not joined_agent:
            query = query.join(User, Property.user_id == User.id, isouter=True).join(
                Agent, User.agent_id == Agent.id, isouter=True
            )

    records = query.order_by(Property.created_at.desc()).all()
    return [serialize_property(record) for record in records]


@app.post("/properties/", response_model=PropertyRead, tags=["properties"])
def create_property(
    payload: PropertyCreate,
    current_user: User = Depends(require_session),
    db: Session = Depends(get_db),
):
    if not current_user.agent_id:
        raise HTTPException(status_code=403, detail="Premium yetkiniz olmadan ilan ekleyemezsiniz.")

    normalized_category = payload.category.lower()
    if normalized_category not in ALLOWED_PROPERTY_CATEGORIES:
        raise HTTPException(status_code=400, detail="Kategori arsa, isyeri veya daire olmalıdır.")

    db_property = Property(
        user_id=current_user.id,
        title=payload.title,
        status=payload.status.lower(),
        category=normalized_category,
        price=payload.price,
        location=payload.location,
        description=payload.description,
        tagline=payload.tagline,
        image_url=payload.image_url,
        area=payload.area,
        rooms=payload.rooms,
        zoning_status=payload.zoning_status,
        floor=payload.floor,
        building_age=payload.building_age,
        featured=payload.featured,
        specs=encode_specs(payload.specs),
    )
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return serialize_property(db_property)


@app.get("/properties/{property_id}", response_model=PropertyRead, tags=["properties"])
def read_property(property_id: int, db: Session = Depends(get_db)):
    db_property = db.get(Property, property_id)
    if not db_property:
        raise HTTPException(status_code=404, detail="Mülk bulunamadı.")
    return serialize_property(db_property)


@app.put("/properties/{property_id}", response_model=PropertyRead, tags=["properties"])
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    current_user: User = Depends(require_session),
    db: Session = Depends(get_db),
):
    db_property = db.get(Property, property_id)
    if not db_property:
        raise HTTPException(status_code=404, detail="Mülk bulunamadı.")
    if db_property.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu ilan üzerinde değişiklik yapma yetkiniz yok.")

    update_data = payload.model_dump(exclude_unset=True)
    if "category" in update_data and update_data["category"]:
        normalized_category = update_data["category"].lower()
        if normalized_category not in ALLOWED_PROPERTY_CATEGORIES:
            raise HTTPException(status_code=400, detail="Kategori arsa, isyeri veya daire olmalıdır.")
        db_property.category = normalized_category
        update_data.pop("category")
    if "status" in update_data and update_data["status"]:
        db_property.status = update_data.pop("status").lower()
    if "specs" in update_data:
        db_property.specs = encode_specs(update_data.pop("specs"))

    for field, value in update_data.items():
        setattr(db_property, field, value)

    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return serialize_property(db_property)


@app.delete("/properties/{property_id}", tags=["properties"])
def delete_property(
    property_id: int,
    current_user: User = Depends(require_session),
    db: Session = Depends(get_db),
):
    db_property = db.get(Property, property_id)
    if not db_property:
        raise HTTPException(status_code=404, detail="Mülk bulunamadı.")
    if db_property.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu ilanı silme yetkiniz yok.")

    db.delete(db_property)
    db.commit()
    return {"detail": "İlan silindi."}


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
    
    for field, value in agent.model_dump().items():
        setattr(db_agent, field, value)

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
