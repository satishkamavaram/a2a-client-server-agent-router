from strands import Agent, tool
from strands_tools import http_request
import asyncpg
from ai_app.logger.log_config import get_app_logger
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from ai_app.llm_models.models import get_model
from ai_app.config.settings import settings


logger = get_app_logger()
# load_dotenv()

agent_postgres_router = APIRouter(
    prefix="/atlas",
    tags=["atlas-postgres"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


class AgentRequest(BaseModel):
    """Request model for the AI agent endpoint"""
    prompt: str = Field(
        ...,
        description="The user's question or prompt to send to the Postgres AI agent",
        min_length=1,
        max_length=10000,
        example="What is the total sales amount for all users in 2024?"
    )


@tool
async def run_sql_query(agent_output):
    """
    Executes a SQL query from agent output.

    Args:
        agent_output (dict): Should have 'query' (str) and optionally 'params' (list/tuple).

    Returns:
        list: Query results as a list of dicts.
    """
   # db_url = "postgresql://admin:admin@host.docker.internal:5432/ai"
    db_url = settings.postgres_url
    conn = await asyncpg.connect(db_url)
    try:
        query = agent_output["query"]
        params = agent_output.get("params", [])
        rows = await conn.fetch(query, *params)
        # Convert asyncpg Record objects to dicts
        return [dict(row) for row in rows]
    finally:
        await conn.close()


@tool
async def generate_sql_query(user_query: str) -> str:
    """
    Generates a valid SQL query for a given user prompt.

    Args:
        user_query (str): The user prompt or query in natural language

    Returns:
        str: Returns a SQL query for executing in PostgreSQL
    """
    prompt = """
    You are a PostgreSQL specialized agent.
    When given a question about the data, generate a SQL query that can be executed in PostgreSQL.
    Always specify the table(s) the query should be run on.
    Extract the following information and return ONLY valid JSON.
    If the query requires parameters (e.g., filtering by user, date, etc.), use parameter placeholders (%s) in the SQL and provide a "params" array with the values in order.

    {
      "query": "SQL query as a string",
      "params": [list of parameter values, or null if not needed]
    }

    RULES:
    - Retrieve only the JSON object, no explanatory text
    - If query is not generated, use null for strings/arrays
    - Use valid table names for the FROM/JOIN clauses
    - Use valid SQL syntax for PostgreSQL
    - For analytical questions (e.g., totals, maximums, rankings, or involving multiple tables), use SQL aggregation functions and JOINs as needed.
    - For questions involving multiple users or multiple sales or multiple customers, use a single query with the IN operator to match all relevant userids and maps all users corrects when joining.
    - Always try to answer with a single query when possible.
    - For questions involving "most", "highest", "top", or "for which customer", use the appropriate aggregation and join clauses.
    - Always output the SQL query as a string in the "query" field in JSON.
    - If no parameters are needed, set "params" to null.
    - sometimes user gives firstname , lastname and customer name in lower case , in sql query include to match case insensitive
    - For questions that require grouping results by user and including related details (such as customer names and sale dates), use aggregation functions like SUM for totals and array_agg for collecting related values (e.g., customer names, sale dates) per user.
    - The output should be one row per user, with total sales, a list of customer names, and a list of sale dates for that user.
    - Always order the results by total sales in descending order unless otherwise specified.
    - Use array_agg(DISTINCT ...) for customer names to avoid duplicates.
    - Ensure the query is compatible with PostgreSQL and can be executed as-is.
    - please use documentation if anytime you are confused and you need help with generating complex and optimized using this url https://neon.com/postgresql/tutorial and use http_request tool
    - If the user does not specify a threshold for "weak sales", you may calculate a threshold such as the 25th percentile or the minimum sales amount, and use that in the query. Mention this in your summary.
    
    Below are the PostgreSQL table schemas:

    users table:
        userid SERIAL PRIMARY KEY,
        firstname TEXT,
        lastname TEXT,
        emailid TEXT,
        gender TEXT

    address table:
        addressid SERIAL PRIMARY KEY,
        userid INT REFERENCES users(userid),
        street TEXT,
        city TEXT,
        state TEXT,
        zip TEXT,
        country TEXT

    customers table:
        customerid SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT

    sales table:
        saleid SERIAL PRIMARY KEY,
        userid INT REFERENCES users(userid),
        customerid INT REFERENCES customers(customerid),
        date DATE,
        amount NUMERIC

    Example record for users: (1, 'Alice', 'Smith', 'alice.smith@example.com', 'Female')
    Example record for address: (1, '123 Main St', 'New York', 'NY', '10001', 'USA')
    Example record for customers: ('Acme Corp', 'contact@acmecorp.com', '555-1001', '100 Acme Way, New York, NY')
    Example record for sales: (1, 1, 101, '2024-01-05', 250.00)
    """
    model = await get_model()
    agent = Agent(model=model, callback_handler=None,
                  system_prompt=prompt, tools=[http_request])
    full_response = ""
    agent_stream = agent.stream_async(user_query)
    async for event in agent_stream:
        if "data" in event:
            chunk = event["data"]
            full_response += chunk
    print(f"SQL query from agent::: {full_response}")
    return full_response


@agent_postgres_router.post("/api/v1/postgres",
                            summary="Atlas AI Agent Postgres Query",
                            description="Send a natural language query to the AI agent for PostgresDB data analysis",
                            response_description="Streaming response with AI agent analysis")
async def agent_response(request: AgentRequest):
    """
    Process a user query through the AI agent system.

    This endpoint accepts natural language queries and uses AI to:
    1. Generate Posgres queries
    2. Execute the queries against the database
    3. Analyze and summarize results

    Args:
        request: AgentRequest containing the user's prompt and optional parameters

    Returns:
        StreamingResponse: Real-time streaming response from the AI agent

    Raises:
        HTTPException: If the request is invalid or processing fails
    """
    try:
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )

        async def response_generator():
            try:
                model = await get_model()
                agent = Agent(
                    model=model,
                    tools=[generate_sql_query, run_sql_query],
                    callback_handler=None,
                    system_prompt="""
                        You are a specialized Postgres db agent.

                        Your tasks:
                        - When given a user question, use the generate_sql_query tool to create an optimized Postgres SQL query.
                        - Use the run_sql_query tool to execute the postgres sql generated query.
                        - After running the query, analyze and summarize the results in clear, concise natural language for the user.
                    """
                )

                # Add context to the prompt if provided
                user_prompt = request.prompt

                agent_stream = agent.stream_async(user_prompt)
                async for event in agent_stream:
                    if "data" in event:
                        yield event["data"]

            except Exception as e:
                logger.error(f"Error in agent processing: {str(e)}")
                yield f"Error: {str(e)}"

        return StreamingResponse(
            response_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in agent_response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
