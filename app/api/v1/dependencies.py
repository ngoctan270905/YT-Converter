from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.db.mongodb import get_database


