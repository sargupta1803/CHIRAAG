from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers import route_router, evidence_router

# Create PostGIS DB tables automatically if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Safety-focused navigation API minimizing exposure to unlit road segments.",
    version="0.1.0",
)

# Restricted to the configured frontend origins. A wildcard combined with
# allow_credentials=True is rejected by browsers anyway, and this API sends
# no cookies or auth headers, so credentials stay off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include routers
app.include_router(route_router)
app.include_router(evidence_router)

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "docs_url": "/docs"
    }