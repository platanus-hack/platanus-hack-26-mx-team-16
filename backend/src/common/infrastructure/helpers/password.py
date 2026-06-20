import bcrypt


def hash_password(raw_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def check_password(raw_password: str, encoded_password: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), encoded_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False
