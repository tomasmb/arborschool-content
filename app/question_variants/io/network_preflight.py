"""Network preflight checks for the hard-variants pipeline."""

from __future__ import annotations

import socket
import subprocess
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
    """Check whether the provider hostname is reachable.

    Prefer Python DNS resolution, but fall back to a lightweight curl HEAD
    request because some local environments have a broken Python resolver
    while system networking still works.
    """
    normalized = provider.strip().lower()
    host = PROVIDER_HOSTS.get(normalized, "")
    if not host:
        return NetworkCheckResult(provider=normalized, host="", ok=False, error="Proveedor no soportado.")
    try:
        socket.getaddrinfo(host, 443)
        return NetworkCheckResult(provider=normalized, host=host, ok=True)
    except OSError as exc:
        curl_result = _check_host_with_curl(host)
        if curl_result is None:
            return NetworkCheckResult(
                provider=normalized,
                host=host,
                ok=False,
                error=f"Python no pudo resolver {host}: {exc}",
            )
        return NetworkCheckResult(provider=normalized, host=host, ok=True, error=f"DNS Python falló, curl sí llegó ({curl_result}).")


def _check_host_with_curl(host: str) -> str | None:
    """Return a short success marker if curl can reach the host."""
    try:
        completed = subprocess.run(
            ["curl", "-I", "--max-time", "10", f"https://{host}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if completed.returncode != 0:
        return None

    for line in completed.stdout.splitlines():
        if line.startswith("HTTP/"):
            return line.strip()
    return "reachable"


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
