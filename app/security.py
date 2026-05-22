from __future__ import annotations

import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)


def require_admin_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    token = os.getenv("API_TOKEN", "dev-token")
    if credentials is None or credentials.credentials != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
