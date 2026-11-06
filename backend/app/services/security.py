import os
import copy
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import bcrypt
import jwt
from fastapi import Request, HTTPException, status

from app.config import (
    ADMIN_USERNAME,
    ADMIN_PASSWORD_HASH,
    ADMIN_PASSWORD,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    SESSION_COOKIE_NAME,
    PORTFOLIO_MODE,
)
from app.services import cache

logger = logging.getLogger("oci-monitor.security")

# Redis key prefix for revoked/blacklisted tokens
KEY_TOKEN_BLACKLIST_PREFIX = "oci:token:blacklist:"


def hash_password(plain_password: str) -> str:
    """Generates a secure bcrypt hash for a plaintext password."""
    # Bcrypt has a 72-byte max password limit
    pw_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str) -> bool:
    """
    Verifies the provided password against ADMIN_PASSWORD_HASH or ADMIN_PASSWORD fallback.
    Uses timing-safe comparison.
    """
    if not plain_password:
        return False

    pw_bytes = plain_password.encode("utf-8")[:72]

    # 1. Check against bcrypt hash if configured
    if ADMIN_PASSWORD_HASH:
        try:
            hash_bytes = ADMIN_PASSWORD_HASH.strip().encode("utf-8")
            if bcrypt.checkpw(pw_bytes, hash_bytes):
                return True
        except Exception as e:
            logger.error(f"Error checking password hash: {e}")

    # 2. Check plain text fallback if hash is not set or failed (e.g., local dev)
    if ADMIN_PASSWORD:
        return secrets.compare_digest(plain_password.strip(), ADMIN_PASSWORD.strip())

    return False


def verify_admin_credentials(username: str, password: str) -> bool:
    """Validates both username and password for single-user admin access."""
    if not username or not password:
        return False
    user_ok = secrets.compare_digest(username.strip(), ADMIN_USERNAME.strip())
    pw_ok = verify_password(password)
    return user_ok and pw_ok


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "role": "admin",
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired.")
        return None
    except jwt.PyJWTError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def get_token_from_request(request: Request) -> Optional[str]:
    """Extracts JWT token from HttpOnly cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()

    return None


async def is_token_blacklisted(token: str) -> bool:
    """Checks if token has been revoked in Redis."""
    try:
        client = cache.get_redis_client()
        # Hash token for consistent short redis key
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"{KEY_TOKEN_BLACKLIST_PREFIX}{token_hash}"
        return await client.exists(key) > 0
    except Exception as e:
        logger.warning(f"Error checking token blacklist in Redis: {e}")
        return False


async def blacklist_token(token: str, exp_seconds: int = 14400) -> None:
    """Revokes a token in Redis until expiration."""
    try:
        client = cache.get_redis_client()
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"{KEY_TOKEN_BLACKLIST_PREFIX}{token_hash}"
        await client.setex(key, exp_seconds, "revoked")
    except Exception as e:
        logger.warning(f"Error blacklisting token: {e}")


async def get_optional_admin(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: returns admin payload if authenticated, else None."""
    token = get_token_from_request(request)
    if not token:
        return None

    if await is_token_blacklisted(token):
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if username == ADMIN_USERNAME:
        return payload

    return None


async def get_current_admin(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: requires valid admin authentication."""
    admin = await get_optional_admin(request)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação administrativa necessária para executar esta operação.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin


# ==============================================================================
# Aggressive Data Masking for Public Portfolio Mode
# ==============================================================================

def mask_ocid(ocid: Optional[str]) -> Optional[str]:
    """
    Aggressively masks an OCI OCID showing minimal characters to avoid leaking tenancy/resource IDs.
    Example: ocid1.tenancy.oc1..aaaa1234 -> ocid1.tenancy...***1234
    """
    if not ocid:
        return ocid
    ocid_str = str(ocid).strip()
    if len(ocid_str) <= 12:
        return "***" + ocid_str[-4:] if len(ocid_str) >= 4 else "***"

    parts = ocid_str.split(".")
    if len(parts) >= 2:
        resource_type = f"ocid1.{parts[1]}"
        return f"{resource_type}...***{ocid_str[-4:]}"
    return f"{ocid_str[:6]}...***{ocid_str[-4:]}"


def mask_ip_address(ip: Optional[str]) -> Optional[str]:
    """
    Aggressively masks IP address leaving only the last octet.
    Example: 129.146.12.34 -> ***.***.***.34
    """
    if not ip:
        return ip
    ip_str = str(ip).strip()
    parts = ip_str.split(".")
    if len(parts) == 4:
        return f"***.***.***.{parts[3]}"
    # IPv6 fallback
    return "***:***:" + ip_str.split(":")[-1] if ":" in ip_str else "***"


def mask_display_name(name: Optional[str], prefix: str = "res") -> Optional[str]:
    """Masks internal hostnames or display names showing minimal characters."""
    if not name:
        return name
    name_str = str(name).strip()
    suffix = ""
    if "(Boot Volume)" in name_str:
        suffix = " (Boot Volume)"
        name_str = name_str.replace("(Boot Volume)", "").strip()
    elif "(Block Volume)" in name_str:
        suffix = " (Block Volume)"
        name_str = name_str.replace("(Block Volume)", "").strip()

    short_end = name_str[-2:] if len(name_str) >= 2 else ""
    return f"{prefix}-***{short_end}{suffix}"


def mask_summary_data(summary: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Aggressively sanitizes summary metrics payload for public portfolio visitors.
    Preserves numerical quotas, burn-rates, and percentages, while masking OCIDs and sensitive names.
    """
    if not summary or not isinstance(summary, dict):
        return summary

    sanitized = copy.deepcopy(summary)

    # Mask Tenancy
    if "tenancy" in sanitized and isinstance(sanitized["tenancy"], dict):
        t = sanitized["tenancy"]
        if "id" in t:
            t["id"] = mask_ocid(t["id"])
        if "name" in t and t["name"]:
            # Display sanitized portfolio tenancy name
            t["name"] = "portfolio-*** (Always Free)"

    # Indicate public portfolio mode in metadata
    sanitized["portfolio_mode"] = True
    return sanitized


def mask_volumes_data(volumes: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """Aggressively masks volumes inventory."""
    if not volumes or not isinstance(volumes, list):
        return volumes

    sanitized_list = []
    for vol in volumes:
        v = copy.deepcopy(vol)
        if "id" in v:
            v["id"] = mask_ocid(v["id"])
        if "attached_instance_id" in v and v["attached_instance_id"]:
            v["attached_instance_id"] = mask_ocid(v["attached_instance_id"])
        if "compartment_id" in v and v["compartment_id"]:
            v["compartment_id"] = mask_ocid(v["compartment_id"])
        if "display_name" in v:
            v["display_name"] = mask_display_name(v["display_name"], "vol")
        if "compartment_name" in v:
            v["compartment_name"] = "root" if v["compartment_name"] == "root" else "comp-***"
        sanitized_list.append(v)
    return sanitized_list


def mask_network_inventory(net_inv: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Aggressively masks network inventory (VCNs, Public IPs, Load Balancers)."""
    if not net_inv or not isinstance(net_inv, dict):
        return net_inv

    sanitized = copy.deepcopy(net_inv)

    if "vcns" in sanitized and isinstance(sanitized["vcns"], list):
        for vcn in sanitized["vcns"]:
            if "id" in vcn:
                vcn["id"] = mask_ocid(vcn["id"])
            if "display_name" in vcn:
                vcn["display_name"] = mask_display_name(vcn["display_name"], "vcn")
            if "compartment_id" in vcn and vcn["compartment_id"]:
                vcn["compartment_id"] = mask_ocid(vcn["compartment_id"])
            if "compartment_name" in vcn and vcn["compartment_name"] != "root":
                vcn["compartment_name"] = "comp-***"
            if "cidr_block" in vcn:
                vcn["cidr_block"] = "10.***.***.0/16"

    if "public_ips" in sanitized and isinstance(sanitized["public_ips"], list):
        for ip_obj in sanitized["public_ips"]:
            if "id" in ip_obj:
                ip_obj["id"] = mask_ocid(ip_obj["id"])
            if "ip_address" in ip_obj:
                ip_obj["ip_address"] = mask_ip_address(ip_obj["ip_address"])
            if "display_name" in ip_obj:
                ip_obj["display_name"] = mask_display_name(ip_obj["display_name"], "ip")
            if "assigned_entity_id" in ip_obj and ip_obj["assigned_entity_id"]:
                ip_obj["assigned_entity_id"] = mask_ocid(ip_obj["assigned_entity_id"])
            if "compartment_id" in ip_obj and ip_obj["compartment_id"]:
                ip_obj["compartment_id"] = mask_ocid(ip_obj["compartment_id"])

    if "unassigned_ips" in sanitized and isinstance(sanitized["unassigned_ips"], list):
        for ip_obj in sanitized["unassigned_ips"]:
            if "id" in ip_obj:
                ip_obj["id"] = mask_ocid(ip_obj["id"])
            if "ip_address" in ip_obj:
                ip_obj["ip_address"] = mask_ip_address(ip_obj["ip_address"])
            if "display_name" in ip_obj:
                ip_obj["display_name"] = mask_display_name(ip_obj["display_name"], "ip")
            if "compartment_id" in ip_obj and ip_obj["compartment_id"]:
                ip_obj["compartment_id"] = mask_ocid(ip_obj["compartment_id"])

    if "load_balancers" in sanitized and isinstance(sanitized["load_balancers"], list):
        for lb in sanitized["load_balancers"]:
            if "id" in lb:
                lb["id"] = mask_ocid(lb["id"])
            if "display_name" in lb:
                lb["display_name"] = mask_display_name(lb["display_name"], "lb")
            if "compartment_id" in lb and lb["compartment_id"]:
                lb["compartment_id"] = mask_ocid(lb["compartment_id"])
            if "ip_addresses" in lb and isinstance(lb["ip_addresses"], list):
                lb["ip_addresses"] = [mask_ip_address(ip) for ip in lb["ip_addresses"]]

    return sanitized


def mask_database_inventory(databases: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """Aggressively masks database inventory."""
    if not databases or not isinstance(databases, list):
        return databases

    sanitized_list = []
    for db in databases:
        d = copy.deepcopy(db)
        if "id" in d:
            d["id"] = mask_ocid(d["id"])
        if "db_name" in d:
            d["db_name"] = mask_display_name(d["db_name"], "db")
        if "display_name" in d:
            d["display_name"] = mask_display_name(d["display_name"], "db")
        if "compartment_name" in d and d["compartment_name"] != "root":
            d["compartment_name"] = "comp-***"
        if "compartment_id" in d and d["compartment_id"]:
            d["compartment_id"] = mask_ocid(d["compartment_id"])
        if "connection_strings" in d:
            d["connection_strings"] = None
        sanitized_list.append(d)
    return sanitized_list


def mask_instances_data(instances: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """
    Aggressively masks compute instances inventory for public visitors.
    Masks OCIDs and private display names, while preserving architecture, OCPUs and memory specs.
    """
    if not instances or not isinstance(instances, list):
        return instances

    sanitized_list = []
    for inst in instances:
        i = copy.deepcopy(inst)
        if "id" in i:
            i["id"] = mask_ocid(i["id"])
        if "display_name" in i:
            i["display_name"] = mask_display_name(i["display_name"], "vm")
        if "compartment_name" in i and i["compartment_name"] != "root":
            i["compartment_name"] = "comp-***"
        if "compartment_id" in i and i["compartment_id"]:
            i["compartment_id"] = mask_ocid(i["compartment_id"])
        sanitized_list.append(i)
    return sanitized_list

