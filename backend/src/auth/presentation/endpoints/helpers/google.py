import httpx
from authlib.jose import JsonWebKey, KeySet, jwt
from fastapi import HTTPException, status

from src.common.domain.entities.auth.google_login import GoogleAuthTokens, GoogleUser
from src.common.application.logging import get_logger
from src.common.settings import settings

logger = get_logger(__name__)


async def get_google_tokens(code: str) -> GoogleAuthTokens:
    token_data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(settings.GOOGLE_TOKEN_URL, data=token_data)
        try:
            response.raise_for_status()  # Lanza una excepción para errores HTTP
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al obtener tokens de Google: {e.response.text}"
            )

        token_response = response.json()
        access_token = token_response.get("access_token")
        id_token = token_response.get("id_token")

        if not access_token or not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudieron obtener tokens de Google válidos."
            )
    return GoogleAuthTokens(access_token=access_token, id_token=id_token)


async def get_google_certs() -> KeySet:
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.GOOGLE_CERTS_URL, timeout=5)
        return JsonWebKey.import_key_set(response.json())


async def verity_google_id_token(id_token: str) -> GoogleUser | None:
    google_key_set = await get_google_certs()
    try:
        claims = jwt.decode(
            id_token,
            key=google_key_set,
            claims_options={"aud": {"values": [settings.GOOGLE_CLIENT_ID]}},
        )
        claims.validate()

        user_email = claims.get("email")
        user_given_name = claims.get("given_name", user_email)
        user_family_name = claims.get("family_name")
        user_picture = claims.get("picture")

        if not user_email:
            logger.error(
                "google.auth.token.invalid",
                reason="email_missing",
                error="ID Token does not contain email",
            )
            return None

        return GoogleUser(
            email=user_email, given_name=user_given_name, family_name=user_family_name, picture=user_picture
        )

    except Exception as e:
        logger.error(
            "google.auth.token.validation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return None
