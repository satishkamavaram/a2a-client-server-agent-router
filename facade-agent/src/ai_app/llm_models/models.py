from typing import Awaitable, Callable, Dict, Optional, Any
import os
from enum import Enum
from strands.models.openai import OpenAIModel
from strands.models import BedrockModel
from strands.models.litellm import LiteLLMModel
from ai_app.config.settings import settings
from ai_app.logger.log_config import get_app_logger
from dotenv import load_dotenv

logger = get_app_logger()
load_dotenv()


def _env_get(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        v = os.getenv(name) or os.getenv(
            name.lower()) or os.getenv(name.upper())
        if v not in (None, ""):
            return v
    return default


def _env_int(*names: str, default: Optional[int] = None) -> Optional[int]:
    v = _env_get(*names)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


def _env_float(*names: str, default: Optional[float] = None) -> Optional[float]:
    v = _env_get(*names)
    try:
        return float(v) if v is not None else default
    except ValueError:
        return default


def _env_bool(*names: str, default: bool = False) -> bool:
    v = _env_get(*names)
    return default if v is None else str(v).strip().lower() in {"1", "true", "yes", "on"}


def _parse_vendor(model_id: str) -> str:
    """Extract vendor prefix from model_id like 'openai/gpt-4o'."""
    return (model_id.split("/", 1)[0] if "/" in model_id else model_id).strip().lower()


async def get_model(
    model_id: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    client_overrides: Optional[Dict[str, Any]] = None,
    params_overrides: Optional[Dict[str, Any]] = None,
) -> LiteLLMModel:
    model_id = model_id if model_id is not None else settings.default_model
    vendor = _parse_vendor(model_id)

    # Vendor-specific overrides from env
    vendor_max = _env_int(f"{vendor}_max_tokens")
    vendor_temp = _env_float(f"{vendor}_temperature")

    final_max = max_tokens if max_tokens is not None else (
        vendor_max if vendor_max is not None else settings.default_max_tokens)
    final_temp = temperature if temperature is not None else (
        vendor_temp if vendor_temp is not None else settings.default_temperature)

    # Client args
    api_base = _env_get(f"{vendor}_api_base", default=None)
    use_proxy = _env_bool(f"{vendor}_llm_proxy", default=False)

    api_key = _env_get(f"{vendor}_api_key")

    client_args: Dict[str, Any] = {
        "api_key": api_key,
        "api_base": api_base,
        "use_litellm_proxy": use_proxy,
    }
    if client_overrides:
        client_args.update(client_overrides)

    params: Dict[str, Any] = {
        "max_tokens": final_max,
        "temperature": final_temp,
    }
    if params_overrides:
        params.update(params_overrides)

    logger.info(
        f"LiteLLMModel init vendor={vendor} model_id={model_id} params={params} client_args={client_args} "
    )

    return LiteLLMModel(
        client_args=client_args,
        model_id=model_id,
        params=params,
    )


class LLM_Vendor(str, Enum):
    openai = "openai"
    bedrock = "bedrock"

# For complete list of model parameters: https://platform.openai.com/docs/api-reference/chat/create.
# For complete set of models: https://platform.openai.com/docs/models


async def get_openai_model(model_id: Optional[str] = None, max_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs):
    logger.info(
        f"model_id: {model_id}, temperature: {temperature} , max_tokens: {max_tokens}")
    logger.info(
        f"settings.openai_model_id: {settings.openai_model_id}, settings.default_max_tokens: {settings.default_max_tokens} , settings.default_temperature: {settings.default_temperature}")
    logger.info(
        f"final.openai_model_id: {model_id or settings.openai_model_id}, final.default_max_tokens: {max_tokens or settings.default_max_tokens} , final.default_temperature: {temperature or settings.default_temperature}")
    model = OpenAIModel(
        model_id=model_id or settings.openai_model_id,
        params={
            "max_tokens": max_tokens or settings.default_max_tokens,
            "temperature": temperature or settings.default_temperature,
        }
    )
    return model


async def get_bedrock_model(aws_region: Optional[str] = None, model_id: str = None, max_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs):
    logger.info(
        f"model_id: {model_id}, temperature: {temperature} , max_tokens: {max_tokens}, aws_region: {aws_region}")
    logger.info(
        f"settings.aws_region: {settings.aws_region}, settings.bedrock_model_id: {settings.bedrock_model_id}, settings.default_max_tokens: {settings.default_max_tokens} , settings.default_temperature: {settings.default_temperature}")

    logger.info(
        f"final.aws_region: {aws_region or settings.aws_region}, final.bedrock_model_id: {model_id or settings.bedrock_model_id}, final.default_max_tokens: {max_tokens or settings.default_max_tokens} , final.default_temperature: {temperature or settings.default_temperature}")

    model = BedrockModel(
        model_id=model_id or settings.bedrock_model_id,
        region_name=aws_region or settings.aws_region,
        max_tokens=max_tokens or settings.default_max_tokens,
        temperature=temperature or settings.default_temperature,
    )
    return model
