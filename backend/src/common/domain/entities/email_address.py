from pydantic import BaseModel, ConfigDict


class RawEmailAddress(BaseModel):
    email: str

    model_config = ConfigDict(
        from_attributes=True,
    )
