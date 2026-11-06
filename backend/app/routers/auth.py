import logging
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends

from app.models.schemas import (
    LoginRequest,
    LoginResponse,
    AuthStatusResponse,
    LogoutResponse,
)
from app.config import (
    ADMIN_USERNAME,
    JWT_EXPIRATION_HOURS,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
)
from app.services.security import (
    verify_admin_credentials,
    create_access_token,
    get_optional_admin,
    get_token_from_request,
    blacklist_token,
)
from app.services.rate_limiter import (
    get_client_ip,
    check_login_brute_force,
    record_login_failure,
    clear_login_failures,
)

logger = logging.getLogger("oci-monitor.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Admin Login",
    description="Authenticates the single administrator, protects against brute-force attacks, and sets an HttpOnly session cookie."
)
async def login(login_req: LoginRequest, request: Request, response: Response):
    client_ip = get_client_ip(request)

    # 1. Check if IP is currently locked out from brute-force attempts
    locked, remaining_seconds = await check_login_brute_force(client_ip)
    if locked:
        logger.warning(f"Login rejected due to active brute-force lock for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login falhas. Tente novamente em {remaining_seconds} segundos.",
            headers={"Retry-After": str(remaining_seconds)},
        )

    # 2. Verify credentials
    valid = verify_admin_credentials(login_req.username, login_req.password)
    if not valid:
        failures = await record_login_failure(client_ip)
        logger.warning(f"Failed login attempt ({failures}) from IP: {client_ip} for user: {login_req.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais de administrador inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Successful login - clear failures and create token
    await clear_login_failures(client_ip)
    token = create_access_token({"sub": ADMIN_USERNAME})

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=JWT_EXPIRATION_HOURS * 3600,
        path="/",
    )

    logger.info(f"Successful admin login from IP: {client_ip}")
    return LoginResponse(
        status="authenticated",
        username=ADMIN_USERNAME,
        token=token,
        role="admin",
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Admin Logout",
    description="Revokes the current JWT session in Redis and clears the authentication cookie."
)
async def logout(request: Request, response: Response):
    token = get_token_from_request(request)
    if token:
        await blacklist_token(token, exp_seconds=JWT_EXPIRATION_HOURS * 3600)

    # Delete session cookie
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return LogoutResponse(status="logged_out")


@router.get(
    "/me",
    response_model=AuthStatusResponse,
    summary="Current Authentication Status",
    description="Returns whether the requester is currently authenticated as administrator or viewing as a portfolio guest."
)
async def get_current_user_status(admin=Depends(get_optional_admin)):
    if admin:
        return AuthStatusResponse(
            authenticated=True,
            username=admin.get("sub", ADMIN_USERNAME),
            role="admin",
        )
    return AuthStatusResponse(
        authenticated=False,
        username=None,
        role="guest",
    )
