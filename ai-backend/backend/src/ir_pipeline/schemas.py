from pydantic import BaseModel


class LLMResponse(BaseModel):
    response: str
    brief: str


class Terms(BaseModel):
    terms: list[str]
