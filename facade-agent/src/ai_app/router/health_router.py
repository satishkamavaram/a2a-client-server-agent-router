from fastapi import APIRouter

health_router = APIRouter(
    prefix="",
    tags=["health"],
    #dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

@health_router.get("/health")
async def health() -> str:
    return "I am healthy!"