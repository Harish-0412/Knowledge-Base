from pydantic import BaseModel


class LLMTestRequest(BaseModel):
    prompt: str


class LLMTestResponse(BaseModel):
    provider: str
    model: str
    ok: bool
    result: dict
