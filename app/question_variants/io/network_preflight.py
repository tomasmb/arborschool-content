"""Network preflight checks for the hard-variants pipeline."""

from __future__ import annotations

import socket
from dataclasses import dataclass


PROVIDER_HOSTS = {
    "openai": "api.openai.com",
    "gemini": "generativelanguage.googleapis.com",
}


@dataclass
class NetworkCheckResult:
    """Outcome of a provider preflight check."""

    provider: str
    host: str
    ok: bool
    error: str = ""


def check_provider_host(provider: str) -> NetworkCheckResult:
    """Check whether Python can resolve the provider hostname."""
    normalized = provider.strip().lower()
    host = PROVIDER_HOSTS.get(normalized, "")
    if not host:
        return NetworkCheckResult(provider=normalized, host="", ok=False, error="Proveedor no soportado.")
    try:
        socket.getaddrinfo(host, 443)
        return NetworkCheckResult(provider=normalized, host=host, ok=True)
    except OSError as exc:
        return NetworkCheckResult(
            provider=normalized,
            host=host,
            ok=False,
            error=f"Python no pudo resolver {host}: {exc}",
        )


def check_required_providers(providers: list[str]) -> list[NetworkCheckResult]:
    """Run unique provider checks in stable order."""
    seen: set[str] = set()
    results: list[NetworkCheckResult] = []
    for provider in providers:
        normalized = provider.strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(check_provider_host(normalized))
    return results
