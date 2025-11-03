from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.core.config import settings

def create_access_token(user_id: int, email: str) ->str:

    #crée un token d'accès JWT de 15 minutes
    payload = {
        "user_id": user_id,
        "email":email,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MIN),
        "type":"access"
    }
    token=jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token

def create_refresh_token(user_id: int, email: str) -> str:
    #crée un token de rafraîchissement JWT au bout de 30 jours 
    payload = {
        "user_id": user_id,
        "email":email,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MIN),
        "type":"refresh"
    }
    token=jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
    
def decode_token(token: str) -> dict:
    payload = verify_token(token)
    if payload is None:
        return None
    return payload.get("user_id")
