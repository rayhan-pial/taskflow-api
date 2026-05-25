from typing import Literal

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    jti: str
    type: Literal["access", "refresh"]


class RefreshRequest(BaseModel):
    refresh_token: str
