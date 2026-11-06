import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app
from app.services.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    mask_ocid,
    mask_ip_address,
    mask_summary_data,
)


@pytest.mark.asyncio
async def test_password_hashing_and_verification():
    """Verify bcrypt hash generation and constant-time verification."""
    raw_pass = "SuperSecurePassword123!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$2b$")

    with patch("app.services.security.ADMIN_PASSWORD_HASH", hashed):
        assert verify_password(raw_pass) is True
        assert verify_password("WrongPassword") is False
        assert verify_password("") is False


@pytest.mark.asyncio
async def test_jwt_creation_and_decoding():
    """Verify JWT token encoding, role assignment and expiration."""
    token = create_access_token({"sub": "admin"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_login_success_sets_cookie(mock_redis):
    """Test POST /api/v1/auth/login sets secure HttpOnly cookie upon valid credentials."""
    raw_pass = "MySecretPass999!"
    hashed = hash_password(raw_pass)

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.services.security.ADMIN_USERNAME", "admin"):
            with patch("app.services.security.ADMIN_PASSWORD_HASH", hashed):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    resp = await ac.post("/api/v1/auth/login", json={"username": "admin", "password": raw_pass})
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["status"] == "authenticated"
                    assert data["username"] == "admin"
                    assert "token" in data
                    assert "oci_admin_session" in resp.cookies


@pytest.mark.asyncio
async def test_login_failure_increments_counter(mock_redis):
    """Test POST /api/v1/auth/login returns 401 on bad password and increments failures."""
    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.services.security.ADMIN_USERNAME", "admin"):
            with patch("app.services.security.ADMIN_PASSWORD_HASH", hash_password("CorrectPass")):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    resp = await ac.post("/api/v1/auth/login", json={"username": "admin", "password": "BadPassword"})
                    assert resp.status_code == 401
                    assert "Credenciais de administrador inválidas" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_brute_force_lockout(mock_redis):
    """Test 5 failed login attempts trigger HTTP 429 lockout."""
    from app.services.rate_limiter import check_login_brute_force, record_login_failure

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        with patch("app.services.security.ADMIN_USERNAME", "admin"):
            with patch("app.services.security.ADMIN_PASSWORD_HASH", hash_password("CorrectPass")):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    # 5 consecutive failures
                    for _ in range(5):
                        resp = await ac.post("/api/v1/auth/login", json={"username": "admin", "password": "Bad"})
                        assert resp.status_code == 401

                    # 6th attempt must be locked out with HTTP 429 (either via RateLimiter or BruteForce lock)
                    locked_resp = await ac.post("/api/v1/auth/login", json={"username": "admin", "password": "Bad"})
                    assert locked_resp.status_code == 429

                # Directly verify the 15-minute brute-force lockout status
                is_locked, remaining = await check_login_brute_force("127.0.0.1")
                assert is_locked is True
                assert remaining > 0


@pytest.mark.asyncio
async def test_logout_revokes_token(mock_redis):
    """Test POST /api/v1/auth/logout revokes session in Redis and clears cookie."""
    token = create_access_token({"sub": "admin"})

    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("oci_admin_session", token)
            resp = await ac.post("/api/v1/auth/logout")
            assert resp.status_code == 200
            assert resp.json()["status"] == "logged_out"

            # Check /auth/me is now guest
            me_resp = await ac.get("/api/v1/auth/me")
            assert me_resp.json()["authenticated"] is False
            assert me_resp.json()["role"] == "guest"


@pytest.mark.asyncio
async def test_auth_me_endpoint_guest_and_admin(mock_redis):
    """Test GET /api/v1/auth/me returns guest vs admin status."""
    with patch("app.services.cache.get_redis_client", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Guest
            g_resp = await ac.get("/api/v1/auth/me")
            assert g_resp.status_code == 200
            assert g_resp.json()["authenticated"] is False
            assert g_resp.json()["role"] == "guest"

            # 2. Admin
            token = create_access_token({"sub": "admin"})
            a_resp = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert a_resp.status_code == 200
            assert a_resp.json()["authenticated"] is True
            assert a_resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_bot_defense_blocks_scanner_user_agent():
    """Test BotDefenseMiddleware blocks known malicious scanners with 403 Forbidden."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/summary", headers={"User-Agent": "sqlmap/1.7#stable"})
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Acesso negado."

        resp_nikto = await ac.get("/api/v1/summary", headers={"User-Agent": "Mozilla/5.0 (Nikto/2.1.6)"})
        assert resp_nikto.status_code == 403


@pytest.mark.asyncio
async def test_aggressive_masking_logic():
    """Test strict masking of sensitive fields for portfolio mode."""
    # OCIDs
    tenancy_ocid = "ocid1.tenancy.oc1..aaaaaaaaxample1234567890abcdef"
    masked_tenancy = mask_ocid(tenancy_ocid)
    assert masked_tenancy.startswith("ocid1.tenancy...")
    assert masked_tenancy.endswith("cdef")
    assert "aaaaaaaaxample" not in masked_tenancy

    volume_ocid = "ocid1.bootvolume.oc1.iad.abuwcljrq"
    masked_vol = mask_ocid(volume_ocid)
    assert masked_vol.startswith("ocid1.bootvolume...")

    # IP addresses
    ip = "129.146.12.34"
    masked_ip = mask_ip_address(ip)
    assert masked_ip == "***.***.***.34"

    # Full summary masking
    summary = {
        "status": "healthy",
        "collected_at": "2026-11-06T12:00:00Z",
        "tenancy": {
            "id": tenancy_ocid,
            "name": "guilherme-personal",
            "home_region": "us-ashburn-1"
        }
    }
    masked_summary = mask_summary_data(summary)
    assert masked_summary["tenancy"]["id"] == masked_tenancy
    assert "portfolio-***" in masked_summary["tenancy"]["name"]
    assert "guilherme" not in masked_summary["tenancy"]["name"]
    assert masked_summary["portfolio_mode"] is True
