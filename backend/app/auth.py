from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Header
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from .settings import get_settings


@dataclass
class Principal:
    key: str
    scopes: List[str]


def _parse_bearer(auth_header: Optional[str]) -> str:
    if not auth_header:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Missing Authorization header"
        )
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header"
        )
    return parts[1]


def get_principal(
    authorization: Optional[str] = Header(default=None, alias="Authorization")
) -> Principal:
    settings = get_settings()
    token = _parse_bearer(authorization)
    scopes = settings.api_keys.get(token)
    if scopes is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return Principal(key=token, scopes=list(scopes))


def require_scope(scope: str) -> Callable[[Principal], Principal]:
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        # Optional Oso integration could be added here; default is simple scope check
        if scope not in principal.scopes:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Insufficient scope"
            )
        return principal

    return dependency
