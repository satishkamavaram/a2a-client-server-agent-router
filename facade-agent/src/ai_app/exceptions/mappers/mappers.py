
from fastapi import FastAPI
from ai_app.exceptions.exception import AIException
from ai_app.models.response.status import ResponseStatus
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ai_app.utils.enum import Status
from ai_app.logger.thread_local_context import get_txid


def register_eception_hadlers(app: FastAPI):
    @app.exception_handler(AIException)
    async def ai_exception(exec: AIException):
        response_status = ResponseStatus(
            status=Status.FAILURE, message=exec.message, txid=get_txid())
        return JSONResponse(status_code=exec.http_code, content=jsonable_encoder(response_status))
