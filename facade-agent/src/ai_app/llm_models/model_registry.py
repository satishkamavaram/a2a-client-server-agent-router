from typing import Awaitable, Callable, Dict, Optional
from ai_app.llm_models.models import get_bedrock_model, get_openai_model
from ai_app.config.settings import settings


model_factory = Callable[..., Awaitable[object]]
MODEL_FACTORIES: Dict[str, model_factory] = {
    "openai": get_openai_model,
    "bedrock": get_bedrock_model,
}


async def get_llm_model(
    vendor: Optional[str] = None,
    **kwargs,
):
    key = (vendor or settings.model_vendor).lower()
    try:
        factory = MODEL_FACTORIES[key]
    except KeyError:
        raise ValueError(f"Unsupported model vendor: {key}")
    return await factory(**kwargs)
