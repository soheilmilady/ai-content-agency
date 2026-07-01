from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.articles import router as articles_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.settings import router as settings_router
from app.core.security import hash_password
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models import User
from app.core.limiter import limiter


def seed_admin() -> None:
    """Bootstrap default admin from env vars safely."""
    admin_email = getattr(settings, "BOOTSTRAP_ADMIN_EMAIL", None)
    admin_password = getattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", None)
    if not admin_email or not admin_password:
        return
        
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == admin_email).first()
        if admin is None:
            admin = User(
                username="admin",
                email=admin_email,
                hashed_password=hash_password(admin_password),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    
    # Load global rate limit from DB
    db = SessionLocal()
    try:
        from app.models.setting import SystemSetting
        import app.core.limiter as limiter_module
        limit_setting = db.query(SystemSetting).filter(SystemSetting.key == "global_daily_rate_limit").first()
        if limit_setting:
            limiter_module.GLOBAL_DAILY_LIMIT = limit_setting.value
        app.state.global_limit = limiter_module.GLOBAL_DAILY_LIMIT
    finally:
        db.close()
        
    yield


app = FastAPI(title="AI Content Agency", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-content-agency.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(articles_router, prefix="/api/v1", tags=["articles"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok"}
