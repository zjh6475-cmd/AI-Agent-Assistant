import bcrypt


MAX_BCRYPT_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")

    if len(encoded) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(
            "密码长度不能超过 72 个字节"
        )

    return encoded


def hash_password(password: str) -> str:
    password_bytes = _password_bytes(password)

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(
    password: str,
    hashed_password: str
) -> bool:
    try:
        return bcrypt.checkpw(
            _password_bytes(password),
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False
    
#使用 bcrypt 加密密码
#限制密码最大长度
#密码错误时返回 False，而不是让接口报 500    
#..\venv\Scripts\python.exe -m py_compile security.py检查语法
