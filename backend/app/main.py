from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import cameras, detection, events, health, tripwire, zones
from app.services.vision import persistence


@asynccontextmanager
async def lifespan(app: FastAPI):
    closed = persistence.close_orphaned_runs()
    if closed:
        print(f"Marked {closed} unfinished detection run(s) as interrupted")
    yield


app = FastAPI(
    title="Crowd Risk System API",
    description="Backend for Real-Time Crowd Density and Flow-Based Risk Prediction",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(events.router)
app.include_router(cameras.router)
app.include_router(zones.router)
app.include_router(tripwire.router)
app.include_router(detection.router)