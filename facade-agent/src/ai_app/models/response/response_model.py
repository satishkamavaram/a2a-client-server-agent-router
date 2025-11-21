from pydantic import BaseModel, Field
from ai_app.models.response.status import ResponseStatus


class AgentResponse(ResponseStatus):
    """Request model for the AI agent endpoint"""
    prompt: str = Field(
        ...,
        description="The user's question or prompt to send to the AI agent",
        min_length=1,
        max_length=10000,
        example="What is the total sales amount for all users in 2024?"
    )
    answer: str = Field(
        ...,
        description="The response from the AI Agent",
    )
