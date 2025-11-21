import logging
import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    OAuthFlows, ClientCredentialsOAuthFlow, OAuth2SecurityScheme
)
from dotenv import load_dotenv
from agent_executor import (
    JiraAgentExecutor,
)

from starlette.responses import JSONResponse
from auth_middleware import OAuth2Middleware
from starlette.middleware import Middleware

load_dotenv()

logging.basicConfig()

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 10002


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):

    skill = AgentSkill(
        id='jira_agent',
        name='Jira Agent',
        description='You are a Jira assistant agent. You can fetch Jira tickets assigned to a user by email and retrieve email IDs for given user IDs. Answer user queries about Jira tickets and user emails using the available tools. You can create appointments',
        tags=['jira'],
        examples=['jira tickets assigned to 1234',
                  'schedule a appointment on 4th sept 2026 at 4:30 am  from email satish.k@test.com and to these users test1@test.com test2@test.com to discuss about future of agentic AI'],
    )

   # app_url = f'http://{host}:{port}'
    app_url = f'http://{host}:10002'
    print(f"app_url:::::{app_url}")
    agent_card = AgentCard(
        name='Jira Agent',
        description='You are a Jira assistant agent. You can fetch Jira tickets assigned to a user by email and retrieve email IDs for given user IDs. Answer user queries about Jira tickets and user emails using the available tools. You can create appointments',
        url=app_url,
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        # authentication=OAuthFlows(
        #        client_credentials=ClientCredentialsOAuthFlow(
        #    tokenUrl="https://localhost:8080/oauth/token",
        #    scopes={
        #        "read:employee_status": "Allows confirming whether a person is an active employee of the company."
        #    },
        # ),

        # authentication={
        #     "schemes": ["Bearer"],
        #     "credentials": "required"  # or "optional" depending on your needs
        # },
        securitySchemes={
            'oauth2': OAuth2SecurityScheme(
                description='',
                flows=OAuthFlows(
                    clientCredentials=ClientCredentialsOAuthFlow(
                        tokenUrl=f'https://localhost:8080/oauth/token',
                        scopes={
                            'read:test': 'Allows confirming',
                        },
                    ),
                ),
            ),
        },
        # security=[{
        #    'oauth2': [
        #        'read:test',
        #    ],
        # }],
    )

    agent_executor = JiraAgentExecutor()
    print(f"agent card:::::{agent_card}")
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    middleware = [
        Middleware(
            OAuth2Middleware,
            agent_card=agent_card,
            public_paths=['/.well-known/agent-card.json',
                          ],
        )
    ]
    app = a2a_app.build(middleware=middleware)

    # app.add_middleware(
    #    OAuth2Middleware,
    #    agent_card=agent_card,
    #    public_paths=['/.well-known/agent-card'],
    # )

    @app.route("/.well-known/agent-card.json", methods=["GET"])
    async def get_agent_card(request):
        return JSONResponse(agent_card.dict())

    @app.route("/test", methods=["GET"])
    async def test_flow(request):
        return JSONResponse(agent_card.dict())

    print(f"agent a2a_app:::::{a2a_app}")
    uvicorn.run(app, host=host, port=port)


@click.command()
@click.option('--host', 'host', default=DEFAULT_HOST)
@click.option('--port', 'port', default=DEFAULT_PORT)
def cli(host: str, port: int):
    main(host, port)


if __name__ == '__main__':
    main()
