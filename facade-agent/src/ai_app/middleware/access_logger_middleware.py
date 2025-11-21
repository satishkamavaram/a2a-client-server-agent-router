from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import datetime
import traceback
from typing import Callable, Awaitable
from ai_app.logger.log_config import get_app_logger
from ai_app.logger.thread_local_context import set_txid, clear_txid
from ai_app.exceptions.exception import AIException
from ai_app.logger.log_config import get_app_logger, get_access_logger

logger = get_app_logger()


class TxidMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            start_time = datetime.datetime.now()
            set_txid()
            response = await call_next(request)
            request_process_time = (
                datetime.datetime.now() - start_time
            ).total_seconds()
            get_access_logger().info(
                f"{request.client.host} {request.method} {request.url.path} {response.status_code} {round(request_process_time)}"
            )
            return response
        except Exception as exec:
            logger.error(
                f"Exception inside transaction middleware: {str(exec)} {traceback.format_exc()}"
            )
            raise AIException(500, "Internal Server Error")
        finally:
            clear_txid()