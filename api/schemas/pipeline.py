from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    days: int = Field(7, ge=1, le=90)
    min_score: int = Field(1, ge=0)


class CollectResult(BaseModel):
    week: str
    fetched: int
    new: int
