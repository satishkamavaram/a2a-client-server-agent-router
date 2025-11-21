import json
import os

from a2a.types import AgentCard
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
import logging
from context_vars import set_access_token, clear_access_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class OAuth2Middleware(BaseHTTPMiddleware):
    """Starlette middleware that authenticates A2A access using an OAuth2 bearer token."""

    def __init__(
        self,
        app: Starlette,
        agent_card: AgentCard = None,
        public_paths: list[str] = None,
    ):
        super().__init__(app)
        self.agent_card = agent_card
        self.public_paths = set(public_paths or [])

        print(f"auth agent card:::::{agent_card}")

    async def dispatch(self, request: Request, call_next):
        try:
            path = request.url.path
            logger.info(f"In Auth Middleware:::::{request.headers}")
            logger.info(f"self.public_paths:::::{self.public_paths}")
            logger.info(f"path:::::{path}")
            # Allow public paths and anonymous access
            if path in self.public_paths:
                return await call_next(request)

            # Authenticate the request
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return self._unauthorized(
                    'Missing or malformed Authorization header.', request
                )

            access_token = auth_header.split('Bearer ')[1]
            logger.info(f"access token received: {access_token}")

            # setting accesss token at context vars so that can be accessed in mcp tools
            set_access_token(access_token)
            return await call_next(request)
        finally:
            # Clear the access token after the request is done
            clear_access_token()
            logger.info(f"::::::sending response:::::::")

    def _forbidden(self, reason: str, request: Request):
        accept_header = request.headers.get('accept', '')
        if 'text/event-stream' in accept_header:
            return PlainTextResponse(
                f'error forbidden: {reason}',
                status_code=403,
                media_type='text/event-stream',
            )
        return JSONResponse(
            {'error': 'forbidden', 'reason': reason}, status_code=403
        )

    def _unauthorized(self, reason: str, request: Request):
        accept_header = request.headers.get('accept', '')
        if 'text/event-stream' in accept_header:
            return PlainTextResponse(
                f'error unauthorized: {reason}',
                status_code=401,
                media_type='text/event-stream',
            )
        return JSONResponse(
            {'error': 'unauthorized', 'reason': reason}, status_code=401
        )
