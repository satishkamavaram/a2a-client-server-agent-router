from fastmcp import FastMCP
import os
import logging
import datetime
from fastmcp.server.dependencies import get_http_headers


CURRENT_YEAR = datetime.datetime.now().year

mcp = FastMCP("jira MCP Server")
logging.basicConfig(level=logging.INFO)
api_key = os.getenv("API_KEY")
config_path = os.getenv("CONFIG_PATH")

logging.info(f"Server received API_KEY: {api_key}")
logging.info(f"Server received config path: {config_path}")


@mcp.tool()
def get_tickets_assigned_to_user(emailId: str) -> list:
    """Get tickets assigned to a user from jira using emailId

    Args:
        emailId: email of the user to get tickets assigned to user. valid emailId format examples like test@test.com , sati.k@cisco.com


    Returns:
        A list of tickets assigned to the user in JSON format (with sensitive data redacted) for a given emailId
    """
    headers = get_http_headers()
    logging.info(f"get tickets assigned to user headers received: {headers}")
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
    headers = get_http_headers()
    logging.info(f"get emailid for userid headers received: {headers}")
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
    headers = get_http_headers()
    logging.info(f"get weather info headers received: {headers}")
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
    headers = get_http_headers()
    logging.info(f"create_appointment headers received: {headers}")
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
        # host="0.0.0.0",
        port=8001
    )
    # mcp.run(transport='stdio')
