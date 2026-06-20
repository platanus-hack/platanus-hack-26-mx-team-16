from pydantic import BaseModel


class GoogleAuthTokens(BaseModel):
    access_token: str
    id_token: str


class GoogleUser(BaseModel):
    email: str
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
