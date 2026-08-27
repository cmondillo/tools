"""FastAPI app: wires the paid /preview endpoint (cache-backed) behind the
x402 gate. Same architecture as link-preview-api's main.py, plus the MCP
mount pattern already proven there and in content-moderation-api.
"""

from __future__ import annotations

import logging
import secrets
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from x402.http.middleware.fastapi import payment_middleware

from . import cache
from .config import Settings, get_settings
from .mcp_server import build_mcp_server
from .payment import build_resource_server, build_routes_config
from .preview import PreviewError, fetch_preview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("link_preview_cache_api")

_FAVICON_BYTES = (Path(__file__).parent / "favicon.png").read_bytes()


class AdminCacheEntry(BaseModel):
    """Same shape as preview.LinkPreview.to_dict() minus 'final_url' (which
    only makes sense for a real fetch that followed redirects) - a manual
    entry has nothing to redirect from."""

    url: str = Field(..., description="Cache key - must match exactly what agents pass as ?url=.")
    title: str | None = None
    description: str | None = None
    image: str | None = None
    favicon: str | None = None
    site_name: str | None = None
    canonical_url: str | None = None
    content_type: str | None = "text/html"


def _check_admin_token(settings: Settings, authorization: str | None) -> None:
    """Every /admin/cache route calls this first. Not x402 - a fixed bearer
    token via ADMIN_TOKEN, since this is for the operator seeding/fixing
    entries by hand (e.g. sites that 403 scrapers - see README), not
    something agents are meant to call."""
    if not settings.admin_token:
        raise HTTPException(503, "Admin routes are not configured (ADMIN_TOKEN unset).")
    provided = (authorization or "").removeprefix("Bearer ").strip()
    if not provided or not secrets.compare_digest(provided, settings.admin_token):
        raise HTTPException(401, "Missing or invalid admin bearer token.")


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

    # Admin-only, bearer-token protected (not x402): let the operator seed
    # or fix a cache entry by hand - e.g. sites that return 403 to any
    # scraper (Coinbase, Dexscreener - see README) can never be served by
    # the normal fetch path, but the data can still be entered manually so
    # agents asking about that URL get a real answer instead of an error.
    # Hidden from /docs (include_in_schema=False): not part of the public
    # product surface, no reason to advertise it to casual API browsers.
    @app.post("/admin/cache", tags=["admin"], include_in_schema=False)
    async def admin_set_cache(
        entry: AdminCacheEntry, authorization: str | None = Header(default=None)
    ) -> dict:
        _check_admin_token(settings, authorization)
        data = entry.model_dump(exclude={"url"})
        data["final_url"] = entry.url
        cache.set(settings.cache_db_path, entry.url, data)
        return {**data, "url": entry.url, "cached": True}

    @app.get("/admin/cache", tags=["admin"], include_in_schema=False)
    async def admin_get_cache(
        url: str = Query(...), authorization: str | None = Header(default=None)
    ) -> dict:
        _check_admin_token(settings, authorization)
        # Admin inspection ignores TTL - useful to see a stale-but-present
        # entry without waiting for it to expire, unlike the paid /preview
        # route which treats an expired entry as a miss.
        data = cache.get(settings.cache_db_path, url, ttl_seconds=float("inf"))
        if data is None:
            raise HTTPException(404, "No cache entry for this URL.")
        return data

    @app.delete("/admin/cache", tags=["admin"], include_in_schema=False)
    async def admin_delete_cache(
        url: str = Query(...), authorization: str | None = Header(default=None)
    ) -> dict:
        _check_admin_token(settings, authorization)
        removed = cache.delete(settings.cache_db_path, url)
        return {"url": url, "removed": removed}

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
