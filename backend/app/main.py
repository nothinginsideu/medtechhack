from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import search, partners, admin, services

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix=f"{settings.API_V1_STR}", tags=["Search"])
app.include_router(partners.router, prefix=f"{settings.API_V1_STR}/partners", tags=["Partners"])
app.include_router(services.router, prefix=f"{settings.API_V1_STR}/services", tags=["Services"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])

from app.db.database import engine
from app.models.base import Base
from app.models.partner import Partner
from app.models.service import Service
from app.models.price_document import PriceDocument
from app.models.price_item import PriceItem
from app.seed import seed_data

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        await seed_data()
        print("Database initialized and seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to MedPartners API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
