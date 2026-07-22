from pydantic import BaseModel, Field


class UserContext(BaseModel):
    background: str
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    constraints: str = ""


class LearningRequest(BaseModel):
    persona_id: str
    goal: str
    time_budget_minutes: int = Field(gt=0)
    user_context: UserContext