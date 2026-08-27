"""FastAPI app: wires the paid /preview endpoint behind the x402 gate.

Request flow for a paying agent:
  1. GET /preview?url=... with no payment -> 402 with a signed price quote.
  2. Agent signs a USDC payment authorization locally and retries the same
     request with an X-PAYMENT header.
  3. Middleware verifies + settles the payment via the configured facilitator.
  4. On success, the request reaches preview() below and gets billed data back.

Exposes create_app() as a factory (rather than a single module-level app)
so tests can spin up isolated instances — the x402 middleware caches
"have I synced with the facilitator yet" state for the lifetime of the
instance it's built into, and tests that exercise that first-sync path
need a clean one each time.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from x402.http.middleware.fastapi import payment_middleware

from .config import Settings, get_settings
from .payment import build_resource_server, build_routes_config
from .preview import PreviewError, fetch_preview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("link_preview_api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    resource_server = build_resource_server(settings)
    routes = build_routes_config(settings)
    # Built once per app instance (not per-request) so the middleware's lazy
    # facilitator-sync state actually persists across requests.
    payment_gate = payment_middleware(
        routes,
        resource_server,
        sync_facilitator_on_start=settings.sync_facilitator_on_start,
    )

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Pay-per-call link preview metadata for AI agents, priced and settled "
            "over the x402 protocol. Send a public URL, get back clean Open Graph "
            f"metadata. {settings.price_usd} per call in USDC on {settings.network}. "
            "No API key, no signup — just pay and call."
        ),
        version="1.0.0",
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
            # The x402 library only catches its own FacilitatorResponseError;
            # a lower-level transport failure (facilitator down, DNS failure,
            # egress blocked) would otherwise surface as a raw 500. Convert it
            # into a clean, honest error instead of an internal traceback leak.
            logger.error("x402 facilitator unreachable: %s", exc)
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Payment facilitator is temporarily unreachable. Please retry shortly."
                },
            )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/", tags=["meta"])
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "protocol": "x402",
            "price": settings.price_usd,
            "network": settings.network,
            "pay_to": settings.pay_to_address,
            "endpoint": "GET /preview?url=<public http(s) url>",
            "docs": "/docs",
        }

    @app.get("/preview", tags=["preview"])
    async def preview(
        url: str = Query(..., description="Public http(s) URL to fetch metadata for."),
    ) -> dict:
        try:
            result = await fetch_preview(
                url, timeout=settings.request_timeout, max_bytes=settings.max_response_bytes
            )
        except PreviewError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return result.to_dict()

    return app


# Module-level instance for `uvicorn app.main:app`.
app = create_app()
