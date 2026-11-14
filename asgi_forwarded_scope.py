"""
RFC 7239 `Forwarded` host authority parser and ASGI sub-mount `Request.scope`
preservation middleware for `alfrexo95/bounty-bot#53`.

Ensures that when an ASGI application or `Request` is sub-mounted under a nested
`root_path`, the original RFC 7239 `Forwarded` `host` authority (including IPv6
bracketed authorities and explicit ports) and `proto` scheme are preserved in
`scope` rather than being overwritten by the sub-mount path or internal upstream
server tuple.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Mapping

_FORWARDED_PAIR_RE = re.compile(
    r'([A-Za-z0-9!#$%&*+.^_`|~-]+)=(?:"((?:\\.|[^"\\])*)"|([^;,\s]+))'
)


def parse_rfc7239_forwarded(header_value: str) -> list[dict[str, str]]:
    """
    Parse an RFC 7239 `Forwarded` header into a list of hop dictionaries.
    Supports quoted values (such as IPv6 `host="[2001:db8::1]:8443"`) and
    escaped characters inside quoted-strings.
    """
    if not header_value or not header_value.strip():
        return []

    hops: list[dict[str, str]] = []
    # Split on commas outside double quotes
    elements: list[str] = []
    current: list[str] = []
    in_quotes = False
    escape = False
    for ch in header_value:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            current.append(ch)
            continue
        if ch == "," and not in_quotes:
            elements.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        elements.append("".join(current).strip())

    for element in elements:
        if not element:
            continue
        hop: dict[str, str] = {}
        for match in _FORWARDED_PAIR_RE.finditer(element):
            key = match.group(1).lower()
            quoted_val = match.group(2)
            token_val = match.group(3)
            if quoted_val is not None:
                val = re.sub(r"\\(.)", r"\1", quoted_val).strip()
            else:
                val = (token_val or "").strip()
            if val and key not in hop:
                hop[key] = val
        if hop:
            hops.append(hop)
    return hops


def split_host_authority(authority: str, default_scheme: str = "http") -> tuple[str, int]:
    """
    Split an RFC 7239 / RFC 3986 host authority (`example.com:8080` or `[::1]:8443`)
    into `(hostname, port)`.
    """
    default_port = 443 if default_scheme.lower() in ("https", "wss") else 80
    auth = authority.strip()
    if auth.startswith("["):
        bracket_end = auth.find("]")
        if bracket_end != -1:
            host_only = auth[: bracket_end + 1]
            rest = auth[bracket_end + 1 :]
            if rest.startswith(":") and rest[1:].isdigit():
                return host_only, int(rest[1:])
            return host_only, default_port
    if ":" in auth:
        host_part, port_part = auth.rsplit(":", 1)
        if port_part.isdigit():
            return host_part, int(port_part)
    return auth, default_port


def extract_forwarded_host_and_scheme(
    headers: Iterable[tuple[bytes, bytes]],
) -> tuple[str | None, str | None]:
    """
    Extract the client-facing `(host_authority, scheme)` from ASGI `scope["headers"]`,
    prioritizing RFC 7239 `Forwarded` (`host=...;proto=...`) over `X-Forwarded-Host`
    and `X-Forwarded-Proto`.
    """
    forwarded_values: list[str] = []
    x_forwarded_host: str | None = None
    x_forwarded_proto: str | None = None

    for raw_k, raw_v in headers:
        k = raw_k.decode("latin-1").lower()
        v = raw_v.decode("latin-1").strip()
        if k == "forwarded":
            forwarded_values.append(v)
        elif k == "x-forwarded-host" and x_forwarded_host is None and v:
            x_forwarded_host = v.split(",")[0].strip()
        elif k == "x-forwarded-proto" and x_forwarded_proto is None and v:
            x_forwarded_proto = v.split(",")[0].strip().lower()

    if forwarded_values:
        combined = ", ".join(forwarded_values)
        hops = parse_rfc7239_forwarded(combined)
        host_auth: str | None = None
        proto: str | None = None
        for hop in hops:
            if host_auth is None and hop.get("host"):
                host_auth = hop["host"]
            if proto is None and hop.get("proto"):
                proto = hop["proto"].lower()
        if host_auth or proto:
            return host_auth or x_forwarded_host, proto or x_forwarded_proto

    return x_forwarded_host, x_forwarded_proto


def preserve_forwarded_authority_in_scope(
    scope: Mapping[str, Any],
    submount_root_path: str | None = None,
) -> dict[str, Any]:
    """
    Return a copy of the ASGI `scope` with the RFC 7239 `Forwarded` host authority
    and scheme preserved across sub-mounts:
    - Sets `scope["forwarded_host"]` and `scope["host"]` to the authoritative
      RFC 7239 `Forwarded` host (or existing `scope["forwarded_host"]` if already
      resolved by an outer mount).
    - Synchronizes the `host` header in `scope["headers"]` and `scope["server"]`
      so downstream `Request(scope).url` / `Request.base_url` retain the external
      host authority when `root_path` is updated by a sub-mount.
    """
    updated = dict(scope)
    raw_headers = list(updated.get("headers") or [])
    header_host, header_proto = extract_forwarded_host_and_scheme(raw_headers)

    effective_scheme = (
        header_proto
        or updated.get("forwarded_proto")
        or updated.get("scheme")
        or "http"
    )
    effective_host = (
        updated.get("forwarded_host")
        or header_host
    )

    if not effective_host:
        for rk, rv in raw_headers:
            if rk.decode("latin-1").lower() == "host":
                effective_host = rv.decode("latin-1").strip()
                break

    if header_proto:
        updated["forwarded_proto"] = header_proto
        updated["scheme"] = header_proto

    if effective_host:
        updated["forwarded_host"] = effective_host
        updated["host"] = effective_host
        hostname, port = split_host_authority(effective_host, effective_scheme)
        updated["server"] = (hostname.strip("[]"), port)

        new_headers: list[tuple[bytes, bytes]] = []
        replaced_host = False
        for rk, rv in raw_headers:
            if rk.decode("latin-1").lower() == "host":
                if not replaced_host:
                    new_headers.append((b"host", effective_host.encode("latin-1")))
                    replaced_host = True
            else:
                new_headers.append((rk, rv))
        if not replaced_host:
            new_headers.insert(0, (b"host", effective_host.encode("latin-1")))
        updated["headers"] = new_headers

    if submount_root_path is not None:
        prefix = "/" + submount_root_path.strip("/") if submount_root_path.strip("/") else ""
        existing_root = (updated.get("root_path") or "").rstrip("/")
        updated["root_path"] = f"{existing_root}{prefix}"
        path = updated.get("path") or "/"
        if prefix and path.startswith(prefix):
            stripped = path[len(prefix) :]
            updated["path"] = stripped if stripped.startswith("/") else f"/{stripped}"

    return updated


class SubMountedForwardedHostMiddleware:
    """
    ASGI middleware that preserves RFC 7239 `Forwarded` host authority across
    sub-mounted applications.
    """

    def __init__(self, app: Callable, submount_root_path: str | None = None) -> None:
        self.app = app
        self.submount_root_path = submount_root_path

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") in ("http", "websocket"):
            scope = preserve_forwarded_authority_in_scope(scope, self.submount_root_path)
        await self.app(scope, receive, send)
