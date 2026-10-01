from fastapi import FastAPI

from app.routers import health

app = FastAPI(
    title="Crowd Risk System API",
    description="Backend for Real-Time Crowd Density and Flow-Based Risk Prediction",
    version="0.1.0",
)

app.include_router(health.router)