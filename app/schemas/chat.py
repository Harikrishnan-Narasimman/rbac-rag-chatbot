from typing import Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="The message to send to the chatbot.")

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    department_scope: Optional[list[str]] = None