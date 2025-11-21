from strands import Agent, tool
from strands_tools import http_request

from fastapi.responses import StreamingResponse
from typing import Optional, Annotated, Literal
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from ai_app.models.request.request_model import AgentRequest
from ai_app.llm_models.models import LLM_Vendor
from ai_app.llm_models.models import get_model
from ai_app.logger.log_config import get_app_logger
logger = get_app_logger()
# load_dotenv()

atlas_agent_router = APIRouter(
    prefix="/atlas",
    tags=["atlas-agent"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


async def resolve_model(
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    return await get_model(
        model_id=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )


@atlas_agent_router.post(
    "/api/v1/agent",
    summary="Atlas AI Agent Query",
    description="Send a natural language query to the AI agent",
    response_description="Response with AI agent analysis",
)
async def agent_response(
    request: AgentRequest,
    model: Annotated[
        Optional[str],
        Query(
            description="LLM Vendor Model(e.g., 'openai/gpt-4-turbo', 'anthropic/claude-3-sonnet','bedrock/us.amazon.nova-lite-v1:0').",
        ),
    ] = None,
    max_tokens: Annotated[
        Optional[int],
        Query(
            description="Max tokens in LLM response",
        ),
    ] = None,
    temperature: Annotated[
        Optional[float],
        Query(
            ge=0.0,
            le=2.0,
            description="LLM Sampling temperature",
        ),
    ] = None,
    aws_region: Annotated[
        Optional[str],
        Query(
            description="AWS Region",
        ),
    ] = None,
):
    logger.info(
        f"model: {model} temperature: {temperature} , max_tokens: {max_tokens}, aws_region: {aws_region}")
    model = await resolve_model(model,
                                max_tokens, temperature)
    logger.info(f"model selected::::{model}")
    return "thanks"
