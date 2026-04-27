from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.inference import router as inference_router
from app.core.config import settings
from app.services.inference_service import get_inference_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_inference_service()  # warm-up: pre-load models at startup
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the SummVi Model Service"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(inference_router, prefix="/v1", tags=["Inference"])
