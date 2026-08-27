"""FastAPI app: wires the paid /moderate endpoint behind the x402 gate.

Same architecture as link-preview-api's main.py: create_app() factory
(tests need isolated facilitator-sync state per instance), a middleware
that converts a facilitator-unreachable error into a clean 503 instead of
a raw 500, and free /, /healthz, /favicon.ico meta routes.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from x402.http.middleware.fastapi import payment_middleware

from .config import Settings, get_settings
from .mcp_server import build_mcp_server
from .moderation import ModerationError, moderate
from .payment import build_resource_server, build_routes_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("content_moderation_api")

_FAVICON_BYTES = (Path(__file__).parent / "favicon.png").read_bytes()


class ModerateRequest(BaseModel):
    text: str = Field(..., description="Text to check. Max 50,000 characters.")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    resource_server = build_resource_server(settings)

    # Same product, sold over MCP too: mount the streamable-HTTP MCP app at
    # /mcp on this same deployment, so there's one public URL an MCP client
    # (or the MCP Registry) can point at - no separate service to run or
    # deploy. Payment enforcement for /mcp itself lives in mcp_server.py; the
    # HTTP payment gate below only covers "POST /moderate" (see
    # build_routes_config), so it doesn't interfere with /mcp.
    #
    # Unlike the HTTP /moderate route (which can lazily sync on its first
    # request, see sync_facilitator_on_start below), the MCP tool has to
    # declare its price/accepts at construction time, so this needs the
    # facilitator's supported schemes known right now, synchronously. If the
    # facilitator happens to be down at exactly this moment, don't take the
    # whole app down with it - skip mounting /mcp for this run (fixed by the
    # next restart/redeploy) and let /moderate keep working as it always
    # has. This is the same "don't crash on a facilitator hiccup" contract
    # as the try/except around payment_gate below, just at startup instead
    # of per-request.
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
        # The MCP session manager needs its lifespan run for streamable HTTP
        # to work; FastAPI doesn't propagate a mounted sub-app's lifespan on
        # its own, so wire it in explicitly.
        async with AsyncExitStack() as stack:
            if mcp_app is not None:
                await stack.enter_async_context(mcp_app.router.lifespan_context(app))
            yield

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Pay-per-call profanity/explicit-content detection for AI agents, priced "
            "and settled over the x402 protocol. Send text, get back a flag, matched "
            f"terms, and a redacted version. {settings.price_usd} per call in USDC on "
            f"{settings.network}. No API key, no signup - just pay and call."
        ),
        version="1.0.0",
        contact={"name": settings.app_name, "email": settings.contact_email},
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
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
            "endpoint": "POST /moderate {\"text\": \"...\"}",
            "docs": "/docs",
        }

    @app.get("/favicon.ico", tags=["meta"], openapi_extra={"security": []})
    async def favicon() -> Response:
        return Response(content=_FAVICON_BYTES, media_type="image/png")

    @app.post("/moderate", tags=["moderate"])
    async def moderate_text(body: ModerateRequest) -> dict:
        try:
            result = moderate(body.text)
        except ModerationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return result.to_dict()

    if mcp_app is not None:
        app.mount("/mcp", mcp_app)

    return app


# Module-level instance for `uvicorn app.main:app`.
app = create_app()
