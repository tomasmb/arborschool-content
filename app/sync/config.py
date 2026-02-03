"""Database configuration for sync operations.

Supports multiple environments: local, staging, and production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

# Type alias for sync environment
SyncEnvironment = Literal["local", "staging", "prod"]


@dataclass
class DBConfig:
    """Database configuration for connecting to Postgres."""

    host: str
    port: int
    database: str
    user: str
    password: str
    # Store original connection string if provided (for SSL params, etc.)
    _connection_string: str | None = None

    @classmethod
    def from_env(cls) -> "DBConfig":
        """Create config from legacy HOST/PORT environment variables (local DB)."""
        host = os.getenv("HOST")
        if not host:
            msg = "HOST environment variable is required for local DB"
            raise ValueError(msg)

        return cls(
            host=host,
            port=int(os.getenv("PORT", "5432")),
            database=os.getenv("DB_NAME", ""),
            user=os.getenv("DB_USER", ""),
            password=os.getenv("DB_PASSWORD", ""),
        )

    @classmethod
    def from_connection_string(cls, url: str) -> "DBConfig":
        """Create config from a DATABASE_URL connection string.

        Args:
            url: PostgreSQL connection URL (e.g., postgresql://user:pass@host:port/db?params)

        Returns:
            DBConfig instance
        """
        parsed = urlparse(url)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") if parsed.path else "",
            user=parsed.username or "",
            password=parsed.password or "",
            _connection_string=url,  # Store original for SSL params
        )

    @classmethod
    def for_environment(cls, environment: SyncEnvironment) -> "DBConfig":
        """Create config for the specified environment.

        Args:
            environment: One of 'local', 'staging', or 'prod'

        Returns:
            DBConfig for the specified environment

        Raises:
            ValueError: If environment config is not found
        """
        if environment == "local":
            return cls.from_env()

        if environment == "staging":
            url = os.getenv("DATABASE_URL_STAGING")
            if not url:
                msg = "DATABASE_URL_STAGING environment variable is required for staging"
                raise ValueError(msg)
            return cls.from_connection_string(url)

        if environment == "prod":
            url = os.getenv("DATABASE_URL_PROD")
            if not url:
                msg = "DATABASE_URL_PROD environment variable is required for prod"
                raise ValueError(msg)
            return cls.from_connection_string(url)

        msg = f"Unknown environment: {environment}"
        raise ValueError(msg)

    @classmethod
    def check_environment_configured(cls, environment: SyncEnvironment) -> bool:
        """Check if the specified environment has required configuration.

        Args:
            environment: One of 'local', 'staging', or 'prod'

        Returns:
            True if environment is configured, False otherwise
        """
        if environment == "local":
            return bool(os.getenv("HOST"))
        if environment == "staging":
            return bool(os.getenv("DATABASE_URL_STAGING"))
        if environment == "prod":
            return bool(os.getenv("DATABASE_URL_PROD"))
        return False

    @property
    def connection_string(self) -> str:
        """Generate psycopg connection string with timeout."""
        # Use original URL if available (preserves SSL params, etc.)
        if self._connection_string:
            # Add timeout if not already present
            sep = "&" if "?" in self._connection_string else "?"
            return f"{self._connection_string}{sep}connect_timeout=5"
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}?connect_timeout=5"
        )
