import pytest

from app.preview import PreviewError, _assert_public_host, _parse_html, _validate_url

SAMPLE_HTML = """
<html>
<head>
  <title>Fallback Title</title>
  <meta property="og:title" content="OG Title" />
  <meta property="og:description" content="OG description text." />
  <meta property="og:image" content="/images/cover.png" />
  <meta property="og:site_name" content="Example Site" />
  <link rel="canonical" href="https://example.com/canonical-path" />
  <link rel="shortcut icon" href="/static/icon.png" />
</head>
<body></body>
</html>
"""

MINIMAL_HTML = """
<html><head><title>Just A Title</title></head><body></body></html>
"""


def test_parse_html_prefers_open_graph_fields():
    result = _parse_html(
        SAMPLE_HTML,
        original_url="https://example.com/page",
        final_url="https://example.com/page",
        content_type="text/html; charset=utf-8",
    )

    assert result.title == "OG Title"
    assert result.description == "OG description text."
    assert result.image == "https://example.com/images/cover.png"
    assert result.site_name == "Example Site"
    assert result.canonical_url == "https://example.com/canonical-path"
    assert result.favicon == "https://example.com/static/icon.png"


def test_parse_html_falls_back_to_title_tag_and_default_favicon():
    result = _parse_html(
        MINIMAL_HTML,
        original_url="https://example.com/page",
        final_url="https://example.com/page",
        content_type="text/html",
    )

    assert result.title == "Just A Title"
    assert result.description is None
    assert result.image is None
    assert result.favicon == "https://example.com/favicon.ico"


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "ftp://example.com/file.txt",
        "javascript:alert(1)",
    ],
)
def test_validate_url_rejects_bad_schemes(url):
    with pytest.raises(PreviewError):
        _validate_url(url)


@pytest.mark.parametrize(
    "hostname",
    [
        "localhost",
        "127.0.0.1",
        "169.254.169.254",  # cloud metadata endpoint
        "10.0.0.5",
        "192.168.1.1",
    ],
)
def test_ssrf_guard_blocks_non_public_hosts(hostname):
    with pytest.raises(PreviewError):
        _assert_public_host(hostname)


def test_ssrf_guard_allows_public_host():
    # A well-known public resolver IP; resolving "8.8.8.8" itself is a no-op
    # getaddrinfo call and doesn't require internet access for the lookup.
    _assert_public_host("8.8.8.8")
