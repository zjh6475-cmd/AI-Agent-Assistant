import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

#密钥从 .env 读取，不再写死。
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "ai-agent-dev-secret-change-me"
)

ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

security = HTTPBearer(auto_error=True)


def create_token(user_id: int):
    payload = {
        "user_id": user_id,
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
   #使用带时区的 UTC 时间，比原来的 datetime.utcnow() 更规范。
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str):
    try:   
        data = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError as error: #捕获 Token 失效、格式错误等异常，并返回 401。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"}
        ) from error

    user_id = data.get("user_id") or data.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        return int(user_id)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户标识",
            headers={"WWW-Authenticate": "Bearer"}
        ) from error


def get_user_id(authorization: str):
    token = authorization.removeprefix("Bearer ").strip()
    return verify_token(token)

# 这是后面把用户身份校验交给 FastAPI 依赖注入使用的接口。
def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    return verify_token(credentials.credentials)



#功能测试
#..\venv\Scripts\python.exe -c "from auth import create_token, verify_token;
# token=create_token(1); print(token[:20]); print(verify_token(token))"