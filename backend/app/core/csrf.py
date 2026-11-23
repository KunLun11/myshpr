"""Origin (CSRF) guard for state-changing requests.

Cookies are ``SameSite=Lax`` already; this is defence in depth for the
same-origin BFF setup (ADR-03). Only requests that carry a browser ``Origin``
(or ``Referer``) are checked, so curl/scripts without those headers keep
working.

Behaviour:

* no configured allowlist in dev -> allow (tests, local tools);
* no configured allowlist in prod -> reject cross-origin browser requests
  (fail closed);
* explicit ``Sec-Fetch-Site: cross-site`` -> reject unsafe methods.
"""

from collections.abc import Iterable
from urllib.parse import urlsplit

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def normalize_origin(value: str) -> str | None:
    """Turn ``Origin``/``Referer`` into ``scheme://host[:port]``."""
    candidate = value.strip()
    if not candidate or candidate == "null":
        return None
    parts = urlsplit(candidate)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


def allowed_origin_set(*groups: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for group in groups:
        for item in group:
            normalized = normalize_origin(item)
            if normalized:
                result.add(normalized)
    return result


def is_request_allowed(
    *,
    method: str,
    origin: str | None,
    referer: str | None,
    fetch_site: str | None,
    allowed: set[str],
    fail_closed: bool,
) -> bool:
    if method.upper() in SAFE_METHODS:
        return True
    if (fetch_site or "").lower() == "cross-site":
        return False

    request_origin = normalize_origin(origin) if origin else None
    if request_origin is None and referer:
        request_origin = normalize_origin(referer)
    if request_origin is None:
        # Non-browser client (no Origin/Referer): nothing to compare against.
        return True
    if not allowed:
        return not fail_closed
    return request_origin in allowed
