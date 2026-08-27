"""FastAPI app: wires the paid /preview endpoint (cache-backed) behind the
x402 gate. Same architecture as link-preview-api's main.py, plus the MCP
mount pattern already proven there and in content-moderation-api.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from x402.http.middleware.fastapi import payment_middleware

from . import cache
from .config import Settings, get_settings
from .mcp_server import build_mcp_server
from .payment import build_resource_server, build_routes_config
from .preview import PreviewError, fetch_preview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("link_preview_cache_api")

_FAVICON_BYTES = (Path(__file__).parent / "favicon.png").read_bytes()


async def _get_preview(settings: Settings, url: str) -> tuple[dict, bool]:
    """Returns (data, was_cache_hit)."""
    cached = cache.get(settings.cache_db_path, url, ttl_seconds=settings.cache_ttl_seconds)
    if cached is not None:
        return cached, True

    result = await fetch_preview(
        url, timeout=settings.request_timeout, max_bytes=settings.max_response_bytes
    )
    data = result.to_dict()
    cache.set(settings.cache_db_path, url, data)
    return data, False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    resource_server = build_resource_server(settings)

    # See content-moderation-api/api/app/main.py for the full rationale on
    # this block (unconditional eager init needed for the MCP tool's
    # accepts, graceful skip-not-crash if the facilitator is down at
    # startup).
    mcp_app = None
    try:
        resource_server.initialize()
        mcp_app = build_mcp_server(settings, resource_server=resource_server).streamable_http_app()
    except httpx.HTTPError as exc:
        logger.error("Skipping /mcp mount: facilitator unreachable at startup: %s", exc)

    routes = build_routes_config(settings)
    payment_gate = payment_middleware(
        routes,
        resource_server,
        sync_facilitator_on_start=settings.sync_facilitator_on_start,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncExitStack() as stack:
            if mcp_app is not None:
                await stack.enter_async_context(mcp_app.router.lifespan_context(app))
            yield

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Pay-per-call link preview metadata for AI agents, at roughly a third of "
            "the price of a fresh-fetch-every-time service - most requests are served "
            "from a shared cache. Priced and settled over the x402 protocol: "
            f"{settings.price_usd} per call in USDC on {settings.network}. No API key, "
            "no signup - just pay and call."
        ),
        version="1.0.0",
        contact={"name": settings.app_name, "email": settings.contact_email},
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
        expose_headers=["X-PAYMENT-RESPONSE", "PAYMENT-RESPONSE"],
    )

    @app.middleware("http")
    async def x402_payment_gate(request: Request, call_next):
        try:
            return await payment_gate(request, call_next)
        except httpx.HTTPError as exc:
            logger.error("x402 facilitator unreachable: %s", exc)
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Payment facilitator is temporarily unreachable. Please retry shortly."
                },
            )

    @app.get("/healthz", tags=["meta"], openapi_extra={"security": []})
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/", tags=["meta"], openapi_extra={"security": []})
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "protocol": "x402",
            "price": settings.price_usd,
            "network": settings.network,
            "pay_to": settings.pay_to_address,
            "endpoint": "GET /preview?url=<public http(s) url>",
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "docs": "/docs",
        }

    @app.get("/favicon.ico", tags=["meta"], openapi_extra={"security": []})
    async def favicon() -> Response:
        return Response(content=_FAVICON_BYTES, media_type="image/png")

    # Free, unpaid: transparency into how well the cache is actually
    # working, not the paid product itself - see README for why this is
    # kept free (it's the receipts for the whole "cheaper because of
    # caching" claim, so it should be checkable by anyone).
    @app.get("/cache-stats", tags=["meta"], openapi_extra={"security": []})
    async def cache_stats() -> dict:
        return cache.stats(settings.cache_db_path)

    @app.get("/preview", tags=["preview"])
    async def preview(
        url: str = Query(..., description="Public http(s) URL to fetch metadata for."),
    ) -> dict:
        try:
            data, was_hit = await _get_preview(settings, url)
        except PreviewError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return {**data, "cached": was_hit}

    if mcp_app is not None:
        app.mount("/mcp", mcp_app)

    return app


# Module-level instance for `uvicorn app.main:app`.
app = create_app()
