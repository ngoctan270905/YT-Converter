import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Union

from fastapi import HTTPException
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from starlette import status

from app.core.config import settings

# Cấu hình băm mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ Kiểm tra mật khẩu khớp với bản băm hay không."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """ Tạo bản băm mật khẩu."""
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """ Tạo JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_token(token: str) -> dict:
    """ Giải mã và xác thực JWT access token. """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
