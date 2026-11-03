import os
import configparser
from pathlib import Path
from typing import Dict, Any, List

# Standard fallback directories inside container or host
FALLBACK_DIRS: List[str] = [
    "/root/.oci",
    "/root/.ssh",
    os.path.expanduser("~/.oci"),
    os.path.expanduser("~/.ssh"),
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
        # Fallback check inside /root/.oci/config
        fallback_cfg = "/root/.oci/config"
        if os.path.isfile(fallback_cfg):
            expanded_config = fallback_cfg
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
