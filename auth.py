import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cachetools import TTLCache
import os

# Configuration from environment variables
COGNITO_REGION = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID")

# JWKS URL for your Cognito User Pool
COGNITO_JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

# Cache JWKS for 1 hour (3600 seconds)
jwks_cache = TTLCache(maxsize=1, ttl=3600)

security = HTTPBearer()


def get_jwks():
    """Fetch and cache JWKS from Cognito"""
    if "jwks" not in jwks_cache:
        response = httpx.get(COGNITO_JWKS_URL)
        response.raise_for_status()
        jwks_cache["jwks"] = response.json()
    return jwks_cache["jwks"]


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify the JWT token from Cognito and return the decoded payload.
    The 'sub' claim contains the unique user ID.
    """
    token = credentials.credentials

    try:
        # Get JWKS
        jwks = get_jwks()

        # Decode header to get the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Find the matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token: Key not found")

        # Verify and decode the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=COGNITO_APP_CLIENT_ID,
            issuer=COGNITO_ISSUER
        )

        return payload

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def get_current_user_id(payload: dict = Depends(verify_token)) -> str:
    """Extract the user ID (sub claim) from the verified token"""
    return payload.get("sub")
