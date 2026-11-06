import os
import configparser
from pathlib import Path
from typing import Dict, Any, List

# Standard fallback directories inside container or host (including Kubernetes Secret mounts and non-root user)
FALLBACK_DIRS: List[str] = [
    "/home/appuser/.oci",
    "/home/appuser/.ssh",
    "/etc/oci",
    "/secrets/oci",
    "/var/run/secrets/oci",
    "/root/.oci",
    "/root/.ssh",
    os.path.expanduser("~/.oci"),
    os.path.expanduser("~/.ssh"),
    "/tmp",
]


def normalize_key_path(key_path: str) -> str:
    """
    Defensively normalizes and resolves the path to an OCI RSA private key file (.pem).
    
    Handles:
    1. Direct paths and tilde expansion (~/.ssh/key.pem -> /root/.ssh/key.pem).
    2. Host paths mounted into standard container locations (/root/.oci or /root/.ssh).
    3. Explicit environment variable OCI_KEY_FILE.
    
    Raises FileNotFoundError with a clear explanation if the key cannot be found.
    """
    if not key_path:
        raise ValueError("key_path cannot be empty or None")

    # 1. Expand ~ and environment variables
    expanded = os.path.expanduser(os.path.expandvars(key_path.strip()))
    if os.path.isfile(expanded):
        return os.path.abspath(expanded)

    # 2. Check if OCI_KEY_FILE env var is explicitly provided
    env_override = os.getenv("OCI_KEY_FILE")
    if env_override and os.path.isfile(env_override):
        return os.path.abspath(env_override)

    # 3. Check fallbacks by basename
    basename = os.path.basename(expanded)
    for fallback_dir in FALLBACK_DIRS:
        candidate = os.path.join(fallback_dir, basename)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    # 4. If not found, raise detailed FileNotFoundError
    checked_locations = [expanded] + [os.path.join(d, basename) for d in FALLBACK_DIRS]
    raise FileNotFoundError(
        f"OCI RSA private key file '{basename}' was not found. "
        f"Attempted locations:\n - " + "\n - ".join(checked_locations)
    )


def load_oci_config(
    config_file: str = None,
    profile_name: str = None
) -> Dict[str, Any]:
    """
    Loads and normalizes the OCI configuration from ~/.oci/config (or custom path).
    Normalizes key_file to ensure compatibility with container mounts.
    """
    if config_file is None:
        config_file = os.getenv("OCI_CONFIG_FILE", "~/.oci/config")
    if profile_name is None:
        profile_name = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")

    expanded_config = os.path.expanduser(config_file)
    if not os.path.isfile(expanded_config):
        # Fallback checks inside non-root home, Kubernetes secrets and container mounts
        fallback_candidates = [
            "/home/appuser/.oci/config",
            "/etc/oci/config",
            "/secrets/oci/config",
            os.path.expanduser("~/.oci/config"),
            "/root/.oci/config",
        ]
        found_cfg = None
        for candidate in fallback_candidates:
            try:
                if os.path.isfile(candidate):
                    found_cfg = candidate
                    break
            except Exception:
                pass
        if found_cfg:
            expanded_config = found_cfg
        else:
            raise FileNotFoundError(f"OCI config file not found at: {config_file}")

    # Read INI config
    parser = configparser.ConfigParser()
    parser.read(expanded_config)

    if profile_name not in parser:
        raise KeyError(f"Profile [{profile_name}] not found in {expanded_config}")

    config_dict = dict(parser[profile_name])

    # Normalize key_file
    if "key_file" in config_dict:
        config_dict["key_file"] = normalize_key_path(config_dict["key_file"])

    return config_dict


# Global application settings
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", "600"))  # 10 minutes
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "900"))  # 15 minutes
OCI_API_DAILY_LIMIT = int(os.getenv("OCI_API_DAILY_LIMIT", "10000"))
OCI_API_RATE_LIMIT_PER_MIN = int(os.getenv("OCI_API_RATE_LIMIT_PER_MIN", "3000"))

# Security and Single-User Admin Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")  # Plain text fallback if hash is not yet generated
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "oci-monitor-secret-replace-in-production-env")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "4"))
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "oci_admin_session")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1", "yes")

# Portfolio & Privacy Mode
PORTFOLIO_MODE = os.getenv("PORTFOLIO_MODE", "true").lower() in ("true", "1", "yes")

# Persistent Storage Configuration
PERSISTENT_DATA_DIR = os.getenv("PERSISTENT_DATA_DIR", "/app/data")
API_USAGE_PERSISTENCE_FILE = os.getenv(
    "API_USAGE_PERSISTENCE_FILE",
    os.path.join(PERSISTENT_DATA_DIR, "api_usage_history.json")
)

# Rate Limiting Settings
RATE_LIMIT_PUBLIC_PER_MINUTE = int(os.getenv("RATE_LIMIT_PUBLIC_PER_MINUTE", "60"))
RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "5"))
RATE_LIMIT_REFRESH_PER_MINUTE = int(os.getenv("RATE_LIMIT_REFRESH_PER_MINUTE", "3"))

# Allowed Origins (CORS)
ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = [origin.strip() for origin in ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

