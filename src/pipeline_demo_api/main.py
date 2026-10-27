"""Application factory, lifecycle, HTTP endpoints, and safe error responses."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from pipeline_demo_api.config import Settings
from pipeline_demo_api.logging import configure_logging
from pipeline_demo_api.models import Health, Info, Item, ItemCreate
from pipeline_demo_api.store import ItemStore, StoreError


def create_app(settings: Settings | None = None, store: ItemStore | None = None) -> FastAPI:
    config = settings or Settings()
    inventory = store or ItemStore()
    logger = configure_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        inventory.initialize()
        logger.info("service_started")
        try:
            yield
        finally:
            inventory.close()
            logger.info("service_stopped")

    application = FastAPI(title=config.name, version=config.version, lifespan=lifespan)

    @application.middleware("http")
    async def log_request(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "status": response.status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return response

    @application.exception_handler(StoreError)
    async def store_error(_: Request, exc: StoreError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"location": list(error["loc"]), "type": error["type"], "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid input.",
                    "details": details,
                }
            },
        )

    @application.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_error", extra={"status": 500})
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An internal error occurred."}},
        )

    @application.get("/health/live", response_model=Health, tags=["health"])
    def live() -> Health:
        return Health(status="alive")

    @application.get("/health/ready", response_model=Health, tags=["health"])
    def ready() -> Health | JSONResponse:
        if not inventory.ready:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "dependencies": {"inventory_store": "unavailable"}},
            )
        return Health(status="ready", dependencies={"inventory_store": "ready"})

    @application.get("/api/v1/info", response_model=Info, tags=["metadata"])
    def info() -> Info:
        return Info(
            name=config.name,
            version=config.version,
            environment=config.environment,
            build_id=config.build_id,
        )

    @application.get("/api/v1/items", response_model=list[Item], tags=["inventory"])
    def list_items() -> list[Item]:
        return inventory.list_items()

    @application.post("/api/v1/items", response_model=Item, status_code=201, tags=["inventory"])
    def create_item(data: ItemCreate) -> Item:
        return inventory.create(data)

    return application


app = create_app()
