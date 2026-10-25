from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database.tables import create_tables
from app.api import (
    sensor_routes,
    reliability_routes,
    vision_routes,
    experience_routes,
    similarity_routes,
    aci_routes,
    cri_routes,
    rola_routes,
    flai_routes,
    tomato_risk_routes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="AgriSight",
    version="0.6.0",
    lifespan=lifespan,
)

app.include_router(sensor_routes.router)
app.include_router(reliability_routes.router)
app.include_router(vision_routes.router)
app.include_router(experience_routes.router)
app.include_router(similarity_routes.router)
app.include_router(aci_routes.router)
app.include_router(cri_routes.router)
app.include_router(rola_routes.router)
app.include_router(flai_routes.router)
app.include_router(tomato_risk_routes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
