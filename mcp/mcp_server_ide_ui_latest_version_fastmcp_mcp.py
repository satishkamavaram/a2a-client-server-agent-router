"""
#latest dependencies
#fastmcp==3.1.0
#mcp==1.26.0
"""
from fastmcp.server.auth import RemoteAuthProvider
from typing import Annotated, Any, Optional
import json
import httpx
from fastmcp import FastMCP
import os
import logging
import datetime
from fastmcp.server.dependencies import get_http_headers, get_access_token

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_headers, get_access_token
from dataclasses import dataclass
from starlette.responses import JSONResponse
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import BaseModel, Field
from typing import List
import datetime
import os
import logging

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_headers, get_access_token
from dataclasses import dataclass
from starlette.responses import JSONResponse
from starlette.routing import Route
from pydantic import AnyHttpUrl
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import BaseModel, Field
from typing import List
import datetime
import os
import logging


logging.basicConfig(level=logging.DEBUG)
CURRENT_YEAR = datetime.datetime.now().year


logging.basicConfig(level=logging.DEBUG)
CURRENT_YEAR = datetime.datetime.now().year

# setup keycloak server : create realm satishrealm and create private client with client id and secret for mcp server

# In Keycloak
# creates 'Visual Studio Code' as client and client_is as random uuid in keycloak and in jwt token aud field value will be None
""" sample decoded jwt token 
{
  "exp": 1757013717,
  "iat": 1757013417,
  "jti": "onrtna:929cf910-370e-9949-8f9b-46ec3913e753",
  "iss": "http://localhost:8080/realms/satishrealm",
  "sub": "8ede11cf-58a5-4bc2-91e2-aebd381f52cc",
  "typ": "Bearer",
  "azp": "ed6bfa06-4b96-4a37-aa29-40cc4f1965f0",
  "sid": "48eb9b22-db6a-4c27-8417-eac0af6092f4",
  "acr": "1",
  "allowed-origins": [
    "http://127.0.0.1:33418",
    "http://127.0.0.1",
    "http://localhost:33418",
    "https://vscode.dev",
    "http://localhost",
    "https://insiders.vscode.dev"
  ],
  "scope": "openid profile email",
  "email_verified": false,
  "name": "s f",
  "preferred_username": "satish2",
  "given_name": "s",
  "family_name": "f",
  "email": "satish2@test.com"
}
"""

"""
configure in mcp.json vscode client

"weather-mcp-server-oauth": {
			"url": "http://127.0.0.1:8000/mcp",
			"type": "http"
		}
"""
token_verifier = JWTVerifier(
    jwks_uri="http://localhost:8080/realms/satishrealm/protocol/openid-connect/certs",
    issuer="http://localhost:8080/realms/satishrealm",
)


"""The core fix was introducing HybridOAuthProxy and using it instead of plain OAuthProxy.
  In FastMCP v3, OAuthProxy mainly expects proxy-issued token flow (great for IDE), so UI’s direct Keycloak bearer token could get 401 invalid_token; HybridOAuthProxy.load_access_token() now tries normal 
  OAuthProxy validation first, then falls back to direct JWTVerifier.verify_token(token) for UI bearer tokens.
  That preserved IDE OAuth behavior while allowing your UI app’s raw bearer token path to authenticate on the same MCP server."""


class HybridOAuthProxy(OAuthProxy):
    async def load_access_token(self, token: str):
        validated = await super().load_access_token(token)
        # For IDE clients - this validated value will have jwt token.. for UI client - it will be None
        logging.info(f"is validated???????????????????????????? {validated}")
        if validated is not None:
            return validated
        # Allow direct upstream bearer tokens (UI flow) in addition to proxy-issued tokens.
        logging.info(
            f"ui flow validated....######################### {validated}")
        return await self._token_validator.verify_token(token)


# Create the auth proxy to enable FastMCP servers to authenticate with OAuth providers that don’t support Dynamic Client Registration (DCR). In this case keycloak.
# create a private client with client id and secret in keycloak for mcp server which helps to create dynamic client registration. In this case, Visual Studio Code public client is created in keycloak.
# use discovery endpoint to get authorization and token endpoints - http://127.0.0.1:8080/realms/satishrealm/.well-known/openid-configuration
auth = HybridOAuthProxy(
    # Provider's OAuth endpoints (from their documentation)
    upstream_authorization_endpoint="http://localhost:8080/realms/satishrealm/protocol/openid-connect/auth",
    upstream_token_endpoint="http://localhost:8080/realms/satishrealm/protocol/openid-connect/token",
    upstream_client_id="testmcpclient",
    upstream_client_secret="ZpyYMtFUelgEuMeijXl3D1hZGrQNzCub",
    # upstream_client_id="testclient",
    # upstream_client_secret="NjoJI3AYor285gPwj0F6fP0LtY4GZy1f",
    token_verifier=token_verifier,
    base_url="http://127.0.0.1:8000",
)


class CompanyAuthProvider(RemoteAuthProvider):
    def __init__(self):
        # handles token validation using IDP provider public keys
        logging.debug(
            "[CompanyAuthProvider] Initializing with JWT validation...")
        token_verifier = JWTVerifier(
            # to fetch public keys for token validation
            jwks_uri="http://localhost:8080/realms/satishrealm/protocol/openid-connect/certs",
            issuer="http://localhost:8080/realms/satishrealm",
            audience="account",  # MUST match the "aud" claim in the JWT token from Keycloak
        )
        logging.debug(
            f"[CompanyAuthProvider] JWTVerifier configured with issuer='http://localhost:8080/realms/satishrealm', audience='account'")

        super().__init__(
            token_verifier=token_verifier,
            authorization_servers=[
                AnyHttpUrl(
                    "http://localhost:8080/realms/satishrealm"
                )  # telling mcp clients list of IDPs to trust
            ],
            resource_server_url="http://127.0.0.1:8000/mcp",  # Your server base URL
        )
        logging.debug(
            "[CompanyAuthProvider] RemoteAuthProvider initialized successfully")

    # this is to just add custom routes , nothing related to token verification
    def get_routes(self) -> list[Route]:
        """Add custom endpoints to the standard protected resource routes."""

        # Get the standard OAuth protected resource routes
        routes = super().get_routes()

        # Add authorization server metadata forwarding for client convenience
        async def authorization_server_metadata(request):
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8080/realms/satishrealm/.well-known/openid-configuration"
                )
                response.raise_for_status()
                return JSONResponse(response.json())

        # /.well-known/oauth-protected-resource
        # /mcp/.well-known/oauth-authorization-server
        routes.append(
            Route(
                "/mcp/.well-known/oauth-protected-resource",
                authorization_server_metadata,
            )
        )

        return routes


# Single server for both IDE + UI clients:
# - IDE clients use OAuth flow via OAuthProxy endpoints.
# - UI clients pass bearer JWTs that are verified by the same token_verifier.
mcp = FastMCP("Weather MCP Server", auth=auth)

# this is just custom endpoint not used during authentication


@mcp.custom_route("/mcp/.well-known/oauth-protected-resource", methods=["GET"])
async def custom_well_known_endpoint(request):
    return JSONResponse(
        {
            "resource": "http://127.0.0.1:8000/mcp",
            "authorization_servers": [
                "http://localhost:8080/realms/satishrealm"
            ],
            "scopes_supported": ["openid", "email", "profile"],
            "bearer_methods_supported": ["header"],
        }
    )


async def _keycloak_openid_metadata() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8080/realms/satishrealm/.well-known/openid-configuration"
        )
        response.raise_for_status()
        return response.json()


# FastMCP v3 + IDE compatibility aliases for auth discovery paths.
@mcp.custom_route("/.well-known/oauth-authorization-server/mcp", methods=["GET"])
async def oauth_authorization_server_mcp_alias(request):
    return JSONResponse(await _keycloak_openid_metadata())


@mcp.custom_route("/.well-known/openid-configuration/mcp", methods=["GET"])
async def openid_configuration_mcp_alias(request):
    return JSONResponse(await _keycloak_openid_metadata())


@mcp.custom_route("/mcp/.well-known/openid-configuration", methods=["GET"])
async def mcp_openid_configuration_alias(request):
    return JSONResponse(await _keycloak_openid_metadata())

CURRENT_YEAR = datetime.datetime.now().year

# mcp = FastMCP("jira MCP Server")
logging.basicConfig(level=logging.INFO)
api_key = os.getenv("API_KEY")
config_path = os.getenv("CONFIG_PATH")

logging.info(f"Server received API_KEY: {api_key}")
logging.info(f"Server received config path: {config_path}")


def _get_request_jwt_token() -> str | None:
    access = get_access_token()
    if access and getattr(access, "token", None):
        return access.token
    headers = get_http_headers(include={"authorization"})
    auth_header = headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1]
    return None


@mcp.tool()
def get_tickets_assigned_to_user(emailId: str) -> list:
    """Get tickets assigned to a user from jira using emailId

    Args:
        emailId: email of the user to get tickets assigned to user. valid emailId format examples like test@test.com , sati.k@cisco.com


    Returns:
        A list of tickets assigned to the user in JSON format (with sensitive data redacted) for a given emailId
    """
    headers = get_http_headers(include={"authorization"})
    jwt_token = _get_request_jwt_token()
    logging.info(f"get tickets assigned to user headers received: {headers}")
    logging.info(
        f"get tickets assigned to user jwt token received: {jwt_token}")
    real_tickets = [
        {
            "ticket_id": "PROJ-2024-001",
            "summary": "Fix authentication vulnerability in user login system",
            "description": "Critical security issue affecting user accounts",
            "assignee": emailId,
            "priority": "HIGH",
            "status": "IN_PROGRESS"
        },
        {
            "ticket_id": "PROJ-2024-002",
            "summary": "Update customer database schema for GDPR compliance",
            "description": "Database contains PII that needs protection",
            "assignee": emailId,
            "priority": "MEDIUM",
            "status": "OPEN"
        },
    ]

    return real_tickets


@mcp.tool()
def get_email_id_from_user_id(user_id: str) -> str:
    """Get email ID from user ID.

    Args:
        user_id: User ID to get email for

    Returns:
        Email ID of the user
    """
    headers = get_http_headers(include={"authorization"})
    jwt_token = _get_request_jwt_token()
    logging.info(f"get emailid for userid headers received: {headers}")
    logging.info(f"get emailid for userid jwt token received: {jwt_token}")
    user_email_map = {
        "user123": "user123@test.com",
        "user456": "user456@test.com"
    }
    return user_email_map.get(user_id, "satish.k@test.com")


@mcp.tool()
async def get_weather_alerts(state: str) -> str:
    """Get weather alerts for a German state.

    Args:
        state: Two-letter German state code (e.g. BW, BY)
    """
    headers = get_http_headers(include={"authorization"})
    jwt_token = _get_request_jwt_token()
    logging.info(f"get weather info headers received: {headers}")
    logging.info(f"get weather info jwt token received: {jwt_token}")
    data = {
        "features": [
            {
                "id": "1",
                "type": "Alert",
                "properties": {
                    "headline": "Severe Thunderstorm Warning",
                    "description": "A severe thunderstorm is approaching your area. Take cover immediately.",
                    "severity": "Severe",
                    "effective": "2024-10-01T14:00:00Z",
                    "expires": "2024-10-01T15:00:00Z"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-120.0, 37.0]
                }
            }
        ]
    }
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Headline: {props.get('headline', 'Unknown')}
Description: {props.get('description', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
"""


@mcp.tool(description=f"Create an appointment with attendees, subject, date, and time. Always provide the date in YYYY-MM-DD format, including the year. If the user omits the year, use {CURRENT_YEAR}.")
def create_appointment(to_emails: list, from_email: str, subject: str, date: str, time: str) -> dict:
    """
    Create an appointment and return confirmation details.

    Args:
        to_emails (list): List of attendee email addresses
        from_email (str): Organizer's email address
        subject (str): Appointment subject
        date (str): Date of the appointment. Format: YYYY-MM-DD (e.g., 2025-09-01). Always include the year. If the user omits the year, use {CURRENT_YEAR}.
        time (str): Time of the appointment. Format: HH:MM (24-hour, e.g., 14:30)
    Returns:
        dict: Confirmation details

    Note:
        - date must always be in ISO format: YYYY-MM-DD (e.g., 2025-09-01). The year is required. If the user omits the year, use {CURRENT_YEAR}.
        - time must be in 24-hour format: HH:MM (e.g., 14:30)
    """
    headers = get_http_headers(include={"authorization"})
    jwt_token = _get_request_jwt_token()
    logging.info(f"create_appointment headers received: {headers}")
    logging.info(f"create_appointment jwt token received: {jwt_token}")
    appointment = {
        "to": to_emails,
        "from": from_email,
        "subject": subject,
        "date": date,
        "time": time,
        "status": "created",
        "appointment_id": f"APT-{date.replace('-', '')}-{time.replace(':', '')}"
    }
    logging.info(f"Appointment created: {appointment}")
    return appointment


if __name__ == "__main__":
    # Run with streamable-http transport for HTTP-based communication in containers
    # Note: FastMCP doesn't support transport_options parameter
    # Session timeout is handled by the underlying transport layer
    """mcp.run(
        transport="streamable-http", 
        host="0.0.0.0", 
        port=8000
    )"""
    mcp.run(
        transport="http",
        stateless_http=True,
        # host="0.0.0.0",
        port=8000
    )
    # mcp.run(transport='stdio')
