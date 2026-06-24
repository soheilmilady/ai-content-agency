from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.articles import router as articles_router
from app.api.v1.endpoints.users import router as users_router
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import User


def seed_admin() -> None:
    """Bootstrap default admin: email=admin@agency.com, password=Admin1234!"""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@agency.com").first()
        if admin is None:
            admin = User(
                username="admin",
                email="admin@agency.com",
                hashed_password=hash_password("Admin1234!"),
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
    yield


app = FastAPI(title="AI Content Agency", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-content-agency-vjbd.vercel.app",
        "https://ai-content-agency-vjbd-gz8r0qc1o-soheilmiladys-projects.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(articles_router, prefix="/api/v1", tags=["articles"])


@app.get("/health")
def health():
    return {"status": "ok"}
