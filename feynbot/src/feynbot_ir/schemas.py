from pydantic import BaseModel


class LLMResponse(BaseModel):
    response: str
    query: str
    brief: str


class Terms(BaseModel):
    terms: list[str]
