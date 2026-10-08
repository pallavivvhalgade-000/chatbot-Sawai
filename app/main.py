from pathlib import Path

from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.chat import router as chat_router
from app.api.schemas import HealthResponse
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.database import initialize_database

from app.api.admin import (
    router as admin_router,
)

from starlette.middleware.trustedhost import (
    TrustedHostMiddleware,
)

from app.api.analytics import (
    router as analytics_router,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from app.api.health import (
    router as health_router,
)

BASE_DIR = Path(__file__).resolve().parent.parent

ADMIN_DIR = BASE_DIR / "admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize application resources when FastAPI starts.
    """

    initialize_database()

    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI customer-support and lead-capture backend "
        "for Sawai Associates."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=(
        settings.allowed_host_list
    ),
)

# ---------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
    ],
)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

app.include_router(
    chat_router
)

app.include_router(
    admin_router
)

app.include_router(
    analytics_router
)

app.include_router(
    health_router
)

app.mount(
    "/staff",
    StaticFiles(
        directory=str(ADMIN_DIR),
        html=True,
    ),
    name="staff",
)


@app.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
    )


@app.middleware("http")
async def security_headers(
    request,
    call_next,
):
    response = await call_next(
        request
    )

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "Referrer-Policy"
    ] = "no-referrer"

    response.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), "
        "microphone=(), "
        "geolocation=()"
    )


    if (
        request.url.path.startswith(
            "/chat"
        )
        or request.url.path.startswith(
            "/admin"
        )
    ):
        response.headers[
            "Cache-Control"
        ] = "no-store"


    return response