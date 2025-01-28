from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    model_name: str = "llama3.2"
