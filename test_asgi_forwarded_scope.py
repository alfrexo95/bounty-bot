import asyncio
from asgi_forwarded_scope import (
    SubMountedForwardedHostMiddleware,
    extract_forwarded_host_and_scheme,
    parse_rfc7239_forwarded,
    preserve_forwarded_authority_in_scope,
    split_host_authority,
)


def test_parse_rfc7239_forwarded_standard_and_ipv6():
    hops = parse_rfc7239_forwarded(
        'for=192.0.2.60;proto=https;host="api.example.org:8443", for="[2001:db8:cafe::17]:4711";host="[::1]:9000"'
    )
    assert len(hops) == 2
    assert hops[0]["host"] == "api.example.org:8443"
    assert hops[0]["proto"] == "https"
    assert hops[1]["host"] == "[::1]:9000"


def test_preserve_forwarded_authority_across_nested_submounts():
    raw_scope = {
        "type": "http",
        "scheme": "http",
        "root_path": "",
        "path": "/v1/subapp/items",
        "server": ("127.0.0.1", 8000),
        "headers": [
            (b"host", b"internal-service:8000"),
            (b"forwarded", b'for=198.51.100.17;host="bounty.example.com:8443";proto=https'),
        ],
    }

    outer_scope = preserve_forwarded_authority_in_scope(raw_scope, submount_root_path="/v1")
    assert outer_scope["forwarded_host"] == "bounty.example.com:8443"
    assert outer_scope["host"] == "bounty.example.com:8443"
    assert outer_scope["scheme"] == "https"
    assert outer_scope["server"] == ("bounty.example.com", 8443)
    assert outer_scope["root_path"] == "/v1"
    assert outer_scope["path"] == "/subapp/items"

    # Simulate inner sub-mount where internal Host header was mutated
    inner_input = dict(outer_scope)
    inner_input["headers"] = [(b"host", b"subapp.local")]
    inner_scope = preserve_forwarded_authority_in_scope(inner_input, submount_root_path="/subapp")
    assert inner_scope["host"] == "bounty.example.com:8443"
    assert inner_scope["forwarded_host"] == "bounty.example.com:8443"
    assert inner_scope["root_path"] == "/v1/subapp"
    assert inner_scope["path"] == "/items"
    assert dict(inner_scope["headers"])[b"host"] == b"bounty.example.com:8443"


def test_submounted_middleware_async_execution():
    captured = {}

    async def dummy_app(scope, receive, send):
        captured["scope"] = scope

    mw = SubMountedForwardedHostMiddleware(dummy_app, submount_root_path="/api")
    scope = {
        "type": "http",
        "path": "/api/bounties",
        "headers": [(b"forwarded", b'host="[2001:db8::1]:8443";proto=https')],
    }
    asyncio.run(mw(scope, lambda: None, lambda msg: None))
    assert captured["scope"]["host"] == "[2001:db8::1]:8443"
    assert captured["scope"]["server"] == ("2001:db8::1", 8443)
    assert captured["scope"]["path"] == "/bounties"
