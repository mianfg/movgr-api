from pydantic import AliasChoices, Field

from src.models.base import MovGrBaseModel


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


class LiveUnsubscribeRequest(MovGrBaseModel):
    token: str
