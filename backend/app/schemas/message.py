from pydantic import BaseModel, Field


class MessagePreviewRequest(BaseModel):
    template: str
    variables: dict[str, str] = Field(default_factory=dict)
