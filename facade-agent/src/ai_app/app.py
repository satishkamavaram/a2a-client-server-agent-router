from fastapi.middleware.cors import CORSMiddleware
from ai_app.logger.log_config import get_app_logger, configure_logging
from ai_app.logger.log_level import get_log_level
from ai_app.middleware.access_logger_middleware import TxidMiddleware
from ai_app.__about__ import __version__
from fastapi import FastAPI
from ai_app.router.health_router import health_router
from ai_app.router.agent_mongo_router import agent_mongo_router
from ai_app.router.agent_postgres_router import agent_postgres_router
from ai_app.router.agent_websocket_router import agent_webosocket_router
from ai_app.router.agent_websocket_router_mcp import agent_webosocket_router_mcp
from ai_app.router.facade_websocket import facade_websocket
from ai_app.router.atlas_router import atlas_agent_router
from ai_app.exceptions.mappers.mappers import register_eception_hadlers
from dotenv import load_dotenv

load_dotenv()

configure_logging(
    app_log_path="./logs/serverlogs/app.log",
    access_log_path="./logs/accesslogs/inbound/inbound_access.log",
    outbound_access_log_path="./logs/accesslogs/outbound/outbound_access.log",
    app_file_log_level=get_log_level("INFO"),
    app_console_log_level=get_log_level("INFO"),
    enable_app_console_logging=True,
    enable_access_logging=True,
    enable_access_console_logging=True,
    enable_outbound_access_logging=True,
    enable_outbound_access_console_logging=True,
    log_retention_in_days=30,
    enable_json_logging=False,
)
logger = get_app_logger()

app = FastAPI()

register_eception_hadlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)
app.add_middleware(TxidMiddleware)
app.title = "AI Agentic APP"
app.description = "AI Agentic APP"
app.version = __version__
# app.servers = [{"url": "http://localhost:8081",
#                "description": "AI dev server"}]


app.include_router(health_router)
app.include_router(agent_mongo_router)
app.include_router(agent_postgres_router)
app.include_router(agent_webosocket_router, include_in_schema=False)
app.include_router(agent_webosocket_router_mcp, include_in_schema=False)
app.include_router(atlas_agent_router)
app.include_router(facade_websocket, include_in_schema=False)
