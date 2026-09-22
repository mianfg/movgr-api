from pydantic import AliasChoices, Field, field_validator

from src.models.base import MovGrBaseModel


def _normalize_token(value: str) -> str:
    token = value.strip().lower()
    if len(token) < 64 or any(char not in "0123456789abcdef" for char in token):
        raise ValueError("invalid APNs device token")
    return token


class LiveSubscribeRequest(MovGrBaseModel):
    token: str
    environment: str = "production"
    kind: str
    stop_id: str = Field(validation_alias=AliasChoices("stopId", "stop_id"))
    preferred_line_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("preferredLineId", "preferred_line_id"),
    )
    metro_direction: str | None = Field(
        default=None,
        validation_alias=AliasChoices("metroDirection", "metro_direction"),
    )
    metro_inverted: bool = Field(
        default=False,
        validation_alias=AliasChoices("metroInverted", "metro_inverted"),
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        return _normalize_token(value)


class LiveUnsubscribeRequest(MovGrBaseModel):
    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        return value.strip().lower()
