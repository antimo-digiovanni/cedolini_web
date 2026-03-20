from pydantic import BaseModel


class EntitySummary(BaseModel):
    name: str
    description: str


class DomainSummaryResponse(BaseModel):
    bounded_contexts: list[str]
    entities: list[EntitySummary]
