import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import inspect, text

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.articles import router as articles_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.settings import router as settings_router
from app.core.security import hash_password
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models import User
from app.core.limiter import limiter

logger = logging.getLogger(__name__)


def migrate_schema():
    """Ensure newly added columns exist in existing database tables."""
    try:
        with engine.connect() as conn:
            insp = inspect(engine)
            if "users" in insp.get_table_names():
                cols = [c["name"] for c in insp.get_columns("users")]
                if "failed_login_attempts" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"))
                if "locked_until" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN locked_until DATETIME DEFAULT NULL"))
                if "token_version" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 1"))
                conn.commit()
    except Exception as exc:
        logger.warning(f"Schema auto-migration notice: {exc}")


def seed_admin() -> None:
    """Bootstrap admin safely without allowing weak default credentials in production."""
    admin_email = getattr(settings, "BOOTSTRAP_ADMIN_EMAIL", None)
    admin_password = getattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", None)
    env = getattr(settings, "ENVIRONMENT", "development").lower()

    if not admin_email or not admin_password:
        return

    if env == "production" and admin_password == "Admin1234!":
        logger.critical(
            "CRITICAL SECURITY ALERT: Cannot bootstrap default admin with password 'Admin1234!' in production! "
            "Please configure a strong, unique BOOTSTRAP_ADMIN_PASSWORD in environment variables."
        )
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
    migrate_schema()
    seed_admin()

    yield


app = FastAPI(title="AI Content Agency", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


from app.api.v1.endpoints.seo import router as seo_router

app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(articles_router, prefix="/api/v1", tags=["articles"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(seo_router, prefix="/api/v1/seo", tags=["seo"])


@app.get("/health")
def health():
    return {"status": "ok"}
