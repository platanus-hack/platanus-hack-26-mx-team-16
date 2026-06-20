from pydantic import BaseModel


class PersonMixin(BaseModel):
    first_name: str | None = None
    last_name: str | None = None


class ProfileMixin(PersonMixin):
    photo_url: str | None = None
