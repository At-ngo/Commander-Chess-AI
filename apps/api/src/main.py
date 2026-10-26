"""
Commander Chess AI — FastAPI Application Entrypoint
Aligned with docs/API_CONTRACT.md
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .routers import health_router, agents_router, games_router, replays_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API platform for Commander Chess AI gameplay, research and agent evaluation.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standardized error response handler for HTTPException
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "details": None,
            }
        },
    )


# Standardized validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu yêu cầu không hợp lệ theo đặc tả API Contract",
                "details": {"errors": exc.errors()},
            }
        },
    )


# Register API v1 Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(agents_router, prefix=api_v1_prefix)
app.include_router(games_router, prefix=api_v1_prefix)
app.include_router(replays_router, prefix=api_v1_prefix)


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{api_v1_prefix}/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.src.main:app", host=settings.HOST, port=settings.PORT, reload=True)
