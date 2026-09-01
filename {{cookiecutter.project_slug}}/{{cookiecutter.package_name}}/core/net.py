"""Client identification behind reverse proxies.

Shared by request logging and rate limiting so both attribute a request to the
same caller.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import get_settings

if TYPE_CHECKING:
    from starlette.requests import Request

UNKNOWN_CLIENT = "unknown"
FORWARDED_FOR_HEADER = "X-Forwarded-For"


def resolve_client_ip(request: Request, trusted_proxy_hops: int) -> str:
    """Return the caller's address, reading ``X-Forwarded-For`` when it is safe.

    ``X-Forwarded-For`` is a chain each proxy appends to, so the rightmost entry
    is the one written by the proxy closest to this app and the leftmost is
    whatever the client claimed. Only the last ``trusted_proxy_hops`` entries
    were added by infrastructure you control; everything to their left is
    attacker-controlled.

    With ``trusted_proxy_hops=0`` the header is ignored entirely — the default,
    because trusting it while directly exposed would let any client rotate the
    header and sidestep every limit. Set it to the exact number of proxies in
    front of the app: too high and the value becomes forgeable again.
    """
    if trusted_proxy_hops > 0:
        chain = [
            part.strip()
            for part in request.headers.get(FORWARDED_FOR_HEADER, "").split(",")
            if part.strip()
        ]
        if len(chain) >= trusted_proxy_hops:
            return chain[-trusted_proxy_hops]
    return request.client.host if request.client else UNKNOWN_CLIENT


def client_ip(request: Request) -> str:
    """``resolve_client_ip`` using the configured proxy depth."""
    return resolve_client_ip(request, get_settings().TRUSTED_PROXY_HOPS)
