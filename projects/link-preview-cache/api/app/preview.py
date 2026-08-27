"""Core fetch/parse logic: given a URL, return its Open Graph / meta preview
metadata. Ported from link-preview-api's app/preview.py rather than imported
across projects (this repo's convention: every project stays fully
self-contained), same battle-tested SSRF hardening kept intact.

SSRF hardening: agents will pass us arbitrary URLs, so before fetching
anything we resolve the hostname and refuse to talk to private, loopback,
link-local, multicast or otherwise non-public addresses. Every redirect hop
is re-validated the same way (an attacker-controlled server could otherwise
302 us to http://169.254.169.254/ etc.).
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import asdict, dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 5
_USER_AGENT = (
    "LinkPreviewCacheBot/1.0 (+https://github.com/cmondillo/tools; "
    "agent-facing link metadata fetcher)"
)


class PreviewError(Exception):
    """Raised for any user-facing failure; carries the HTTP status to return."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class LinkPreview:
    url: str
    final_url: str
    title: str | None
    description: str | None
    image: str | None
    favicon: str | None
    site_name: str | None
    canonical_url: str | None
    content_type: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _assert_public_host(hostname: str) -> None:
    """Raise PreviewError if `hostname` resolves to a non-public address."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise PreviewError(f"Could not resolve host: {hostname}", 422) from exc

    if not infos:
        raise PreviewError(f"Could not resolve host: {hostname}", 422)

    for *_rest, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise PreviewError(
                f"URL resolves to a non-public address and is blocked: {hostname}", 422
            )


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise PreviewError("Only http:// and https:// URLs are supported", 422)
    if not parsed.hostname:
        raise PreviewError("URL must include a hostname", 422)
    _assert_public_host(parsed.hostname)
    return url


def _find_link_href(soup: BeautifulSoup, rel_keywords: tuple[str, ...]) -> str | None:
    """Find the href of the first <link> tag whose rel matches any keyword.

    bs4 normalizes `rel` to a list for most builders but not all, so handle
    both shapes rather than relying on a lambda-based attribute filter.
    """
    for tag in soup.find_all("link", href=True):
        rel = tag.get("rel") or []
        if isinstance(rel, str):
            rel = [rel]
        rel_lower = [r.lower() for r in rel]
        if any(keyword in r for r in rel_lower for keyword in rel_keywords):
            return tag["href"]
    return None


def _meta_content(
    soup: BeautifulSoup, *, property: str | None = None, name: str | None = None
) -> str | None:
    tag = soup.find("meta", attrs={"property": property}) if property else None
    if tag is None and name:
        tag = soup.find("meta", attrs={"name": name})
    content = tag.get("content") if tag else None
    return content.strip() if content else None


def _parse_html(html: str, *, original_url: str, final_url: str, content_type: str) -> LinkPreview:
    soup = BeautifulSoup(html, "html.parser")

    title = _meta_content(soup, property="og:title") or _meta_content(soup, name="twitter:title")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    description = (
        _meta_content(soup, property="og:description")
        or _meta_content(soup, name="twitter:description")
        or _meta_content(soup, name="description")
    )

    image = _meta_content(soup, property="og:image") or _meta_content(soup, name="twitter:image")
    if image:
        image = urljoin(final_url, image)

    site_name = _meta_content(soup, property="og:site_name")

    canonical_href = _find_link_href(soup, ("canonical",))
    canonical_url = urljoin(final_url, canonical_href) if canonical_href else None

    icon_href = _find_link_href(soup, ("icon",))
    favicon = urljoin(final_url, icon_href) if icon_href else urljoin(final_url, "/favicon.ico")

    return LinkPreview(
        url=original_url,
        final_url=final_url,
        title=title,
        description=description,
        image=image,
        favicon=favicon,
        site_name=site_name,
        canonical_url=canonical_url,
        content_type=content_type,
    )


async def fetch_preview(url: str, *, timeout: float, max_bytes: int) -> LinkPreview:
    """Fetch `url` and return its preview metadata. Raises PreviewError on failure."""
    original_url = _validate_url(url)
    current_url = original_url
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            try:
                async with client.stream("GET", current_url, headers=headers) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise PreviewError("Redirect without a Location header", 502)
                        current_url = _validate_url(urljoin(current_url, location))
                        continue

                    if response.status_code >= 400:
                        raise PreviewError(f"Upstream returned HTTP {response.status_code}", 502)

                    content_type = response.headers.get("content-type", "")
                    if "html" not in content_type:
                        raise PreviewError(
                            f"Unsupported content-type for preview: {content_type or 'unknown'}",
                            415,
                        )

                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) >= max_bytes:
                            break
                    html = body[:max_bytes].decode(response.encoding or "utf-8", errors="replace")
                    final_url = str(response.url)
                    break
            except httpx.RequestError as exc:
                raise PreviewError(f"Failed to fetch URL: {exc}", 502) from exc
        else:
            raise PreviewError("Too many redirects", 502)

    return _parse_html(html, original_url=original_url, final_url=final_url, content_type=content_type)
