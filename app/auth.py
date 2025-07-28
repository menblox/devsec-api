from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status
from typing import Any

from fastapi.security import OAuth2PasswordBearer

from datetime import timedelta, datetime
from typing import Optional
import copy

from app.db import Name_JWT

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM

# Создаем контекст для хеширования паролей.
# schemes=["bcrypt"] указывает, что мы будем использовать алгоритм bcrypt.
# deprecated="auto" позволяет passlib автоматически обрабатывать устаревшие хеши,
# если вы когда-либо будете обновлять алгоритмы.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password: str) -> str:
    """
    Хеширует обычный пароль с использованием настроенного контекста.
    Возвращает хешированную строку.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли обычный (нехешированный) пароль
    хранящемуся хешированному паролю.
    Возвращает True, если совпадает, False в противном случае.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    data_copy = copy.deepcopy(data)

    if expires_delta is None:
        now_time = datetime.utcnow()
        token_time = now_time + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    elif expires_delta is not None:
        now_time = datetime.utcnow()
        token_time = now_time + expires_delta

    data_copy["exp"] = token_time

    encoded_jwt = jwt.encode(claims=data_copy, key=SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Name_JWT:
    token_decode = None
    try:
        token_decode = jwt.decode(token=token, key=SECRET_KEY, algorithms=[ALGORITHM])
        name_jwt = token_decode.get("sub")
        if name_jwt is None:
            raise HTTPException(status_code=401, detail="Token is not valid!")
        else:
            name_jwt_1 = Name_JWT(name=name_jwt)
            return name_jwt_1

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Could not validate credentials") from JWTError
