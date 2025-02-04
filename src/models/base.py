from pydantic import BaseModel, ConfigDict


class MovGrBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        exclude_unset=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )
