from contextlib import asynccontextmanager
import traceback
from time import perf_counter
from uuid import uuid4
import sys
from pathlib import Path

# Add project root to sys.path to allow importing 'ml' module
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.history import router as history_router
from app.api.routes.rating import router as rating_router
from app.api.routes.summarize import router as summarize_router
from app.core.config import settings
from app.core.database import init_db
from app.services.auth_service import get_optional_user_id_from_authorization_header
from app.services.system_log_service import determine_log_level, safe_create_system_log, serialize_log_details


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def system_log_middleware(request: Request, call_next):
    started_at = perf_counter()
    request_id = str(uuid4())
    request.state.request_id = request_id
    status_code = 500
    error_message = None
    error_type = None
    user_id = get_optional_user_id_from_authorization_header(request.headers.get("Authorization"))
    route_name = None
    response = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        error_message = str(exc)
        error_type = type(exc).__name__
        raise
    finally:
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        route = request.scope.get("route")
        route_name = getattr(route, "name", None)
        details = {
            "path_params": request.path_params or None,
            "query_params": dict(request.query_params) or None,
            "traceback": traceback.format_exc(limit=8) if error_message else None,
        }
        safe_create_system_log(
            request_id=request_id,
            endpoint=request.url.path,
            route_name=route_name,
            method=request.method,
            log_level=determine_log_level(status_code, error_message),
            status_code=status_code,
            response_time=elapsed_ms,
            user_id=user_id,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            error_type=error_type,
            error_message=error_message,
            details=serialize_log_details(details),
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, _exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error. Please try again later.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/")
def read_root():
    return {"message": "Welcome to the SummVi Vietnamese Summarization API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(ai_router, prefix="/ai", tags=["Summarization"])
app.include_router(history_router, prefix="/history", tags=["History"])
app.include_router(rating_router, prefix="/rating", tags=["Rating"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(summarize_router, prefix=settings.api_prefix, tags=["Legacy"])
