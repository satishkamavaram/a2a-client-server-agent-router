import json
from typing import Optional, Dict, Any, Union, List
import os
from strands.models.litellm import LiteLLMModel
from ai_app.logger.log_config import get_app_logger
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from strands import Agent, tool
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv
from pymongo import MongoClient
from fastapi import HTTPException
from fastapi import APIRouter
from ai_app.llm_models.models import get_model
from ai_app.config.settings import settings
logger = get_app_logger()
# load_dotenv()

# load_dotenv()

agent_mongo_router = APIRouter(
    prefix="/atlas",
    tags=["atlas-mongo"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


# Pydantic Models
class AgentRequest(BaseModel):
    """Request model for the AI agent endpoint"""
    prompt: str = Field(
        ...,
        description="The user's question or prompt to send to the Mongo AI agent",
        min_length=1,
        max_length=10000,
        example="What is the total sales amount for all users in 2024?"
    )


class AgentErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(
        None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


model1 = OpenAIModel(
    # client_args={
    #    "api_key": "<KEY>",
    # },
    # **model_config
    model_id="gpt-4-turbo",
    params={
        "max_tokens": 1000,
        "temperature": 0.7,
    }
)

api_key = os.environ.get('OPENAI_API_KEY')
model1 = LiteLLMModel(
    client_args={
        "api_key": f"{api_key}",
        "api_base": None,
        "use_litellm_proxy": False
    },
    # **model_config
    model_id="openai/gpt-4-turbo",
    params={
        "max_tokens": 100,
        "temperature": 0.7,
    }
)


@tool
async def run_mongodb_query(collection: str,
                            query: Union[List[Dict[str, Any]], Dict[str, Any], str],):
    """
    Executes a MongoDB query (aggregation pipeline or find) from agent output.

    Args:
        collection: MongoDB collection name.
        query: Aggregation pipeline (list) or filter (dict). A JSON string is also accepted.

    Returns:
        list: Query results as a list of dicts.
    """
    logger.info("inside run_mongodb_query")
    # mongo_uri = "mongodb://root:root@host.docker.internal:27017"
    # db_name = "ai"
    mongo_uri = settings.mongo_url
    logger.info(f"mongo_uri::::::{mongo_uri}")
    db_name = settings.mongo_db
    client = MongoClient(mongo_uri)
    db = client[db_name]
    # Accept JSON string and parse
    if isinstance(query, str):
        try:
            query = json.loads(query)
        except Exception as e:
            logger.error(f"Invalid JSON for 'query': {e}; raw={query!r}")
            raise

    coll = db[collection]
    # query = agent_output["query"]

    # If query is a list, treat as aggregation pipeline
    if isinstance(query, list):
        cursor = coll.aggregate(query)
    else:
        cursor = coll.find(query)
    logger.info(f"response fron mongo::::::list(cursor)")
    return list(cursor)


@tool
async def generate_nosql_query(user_query: str) -> str:
    """
    Generates a valid nosql mongodb query for a given user prompt

    Args:
        user_query (str): The user prompt or query in natural language

    Returns:
        str: Returns a valid nosql mongodb query for executing in mongodb server
        Generates a valid MongoDB query description:
            {
            "collection": "<name>",
            "query": <aggregation list or filter dict>
            }
    """
    prompt = """
    You are a mongodb specialized agent.
    When given a question about the data, generate a MongoDB query in the format used by the PyMongo library in Python
    Always specify the collection name the query should be run on.
    Extract following information and return ONLY valid JSON.

    {
      "collection" : "collection name"
      "query": "mongodb query"
    }
    
    RULES:
    - Retrieve only the JSON object, no explanatory text
    - If query is not generated, use null for strings/arrays
    - Include valid collection names for colleciton field in json
    - Include valid mongodb query that can be used in PyMongo library in Python for query field in json
    - For analytical questions (e.g., totals, maximums, rankings, or involving multiple collections), use MongoDB aggregation pipelines.
    - Use $lookup for joining collections, $group for aggregating, $sort for ordering, and $limit for top results.
    - For questions involving multiple users or multiple sales or multiple customers, use a single query with the $in operator to match all relevant userids.
    - Always try to answer with a single query or aggregation pipeline when possible.
    - For questions involving "most", "highest", "top", or "for which customer", use the appropriate aggregation and join stages.
    - Always output the aggregation pipeline as a Python list of dictionaries in the "query" field in json
    
    Below is the mongodb schema with one example record. Use these schemas to generate mongodb query. There are totally 4 mongodb collections 

    users collection schema and one example:
        {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
            "_id",
            "emailid",
            "firstname",
            "gender",
            "lastname",
            "userid"
            ],
            "properties": {
            "_id": {
                "bsonType": "objectId"
            },
            "emailid": {
                "bsonType": "string"
            },
            "firstname": {
                "bsonType": "string"
            },
            "gender": {
                "bsonType": "string"
            },
            "lastname": {
                "bsonType": "string"
            },
            "userid": {
                "bsonType": "int"
            }
            }
        }
        }
        example record: {"userid": 1, "firstname": "Alice", "lastname": "Smith", "emailid": "alice.smith@example.com", "gender": "Female"}
    address collection:
        {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
            "_id",
            "addressid",
            "city",
            "country",
            "state",
            "street",
            "userid",
            "zip"
            ],
            "properties": {
            "_id": {
                "bsonType": "objectId"
            },
            "addressid": {
                "bsonType": "int"
            },
            "city": {
                "bsonType": "string"
            },
            "country": {
                "bsonType": "string"
            },
            "state": {
                "bsonType": "string"
            },
            "street": {
                "bsonType": "string"
            },
            "userid": {
                "bsonType": "int"
            },
            "zip": {
                "bsonType": "string"
            }
            }
        }
        }
        example record:{"addressid": 1, "userid": 1, "street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}
    customers collection:
        {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "_id",
            "address",
            "customerid",
            "email",
            "name",
            "phone"
        ],
        "properties": {
            "_id": {
            "$ref": "#/$defs/ObjectId"
            },
            "address": {
            "type": "string"
            },
            "customerid": {
            "type": "integer"
            },
            "email": {
            "type": "string"
            },
            "name": {
            "type": "string"
            },
            "phone": {
            "type": "string"
            }
        },
        "$defs": {
            "ObjectId": {
            "type": "object",
            "properties": {
                "$oid": {
                "type": "string",
                "pattern": "^[0-9a-fA-F]{24}$"
                }
            },
            "required": [
                "$oid"
            ],
            "additionalProperties": false
            }
        }
        }
        example record:{"customerid": 101, "name": "Acme Corp", "email": "contact@acmecorp.com", "phone": "555-1001", "address": "100 Acme Way, New York, NY"}
    sales collection:
        {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
            "_id",
            "amount",
            "customerid",
            "date",
            "saleid",
            "userid"
            ],
            "properties": {
            "_id": {
                "bsonType": "objectId"
            },
            "amount": {
                "bsonType": "int"
            },
            "customerid": {
                "bsonType": "int"
            },
            "date": {
                "bsonType": "string"
            },
            "saleid": {
                "bsonType": "int"
            },
            "userid": {
                "bsonType": "int"
            }
            }
        }
        }
        example record:{"saleid": 1, "userid": 1, "customerid": 101, "date": "2024-01-05", "amount": 250.00}
    """
    logger.info("inside generate_nosql_query")
    model = await get_model()
    agent = Agent(model=model, callback_handler=None, system_prompt=prompt)
    full_response = ""
    agent_stream = agent.stream_async(user_query)
    async for event in agent_stream:
        if "data" in event:
            chunk = event["data"]
            full_response += chunk
    print(f"mongodb query from agent::: {full_response}")
    return full_response


@agent_mongo_router.post("/api/v1/mongo",
                         summary="Atlas AI Agent Mongo Query",
                         description="Send a natural language query to the AI agent for MongoDB data analysis",
                         response_description="Streaming response with AI agent analysis")
async def agent_response(request: AgentRequest):
    """
    Process a user query through the AI agent system.

    This endpoint accepts natural language queries and uses AI to:
    1. Generate MongoDB queries
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
                    tools=[generate_nosql_query, run_mongodb_query],
                    callback_handler=None,
                    system_prompt="""
                        You are a specialized MongoDB agent.
                        Your tasks:
                        - When given a user question, use the generate_nosql_query tool to create an optimized MongoDB NoSQL query.
                        - Use the run_mongodb_query tool to execute the mongodb nosql generated query.
                        - After running the query, analyze and summarize the results in clear, concise natural language for the user.
                        - Call run_mongodb_query exactly once after you have a valid collection and query.
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
                "X-Accel-Buffering": "no"  # Disable nginx buffering
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


@agent_mongo_router.post("/api/v1/mongo/sync",
                         response_model=Dict[str, Any],
                         summary="AI Agent Mongo Query (Non-streaming)",
                         description="Send a natural language query to the AI agent and get complete response", include_in_schema=False)
async def agent_response_sync(request: AgentRequest):
    """
    Process a user query through the AI agent system and return complete response.

    This endpoint is similar to the streaming version but returns the complete
    response as a single JSON object instead of streaming.

    Args:
        request: AgentRequest containing the user's prompt and optional parameters

    Returns:
        Dict containing the complete AI agent response

    Raises:
        HTTPException: If the request is invalid or processing fails
    """
    try:
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )

        agent = Agent(
            model=model1,
            tools=[generate_nosql_query, run_mongodb_query],
            callback_handler=None,
            system_prompt="""
                You are a specialized MongoDB agent.
                Your tasks:
                - When given a user question, use the generate_nosql_query tool to create an optimized MongoDB NoSQL query.
                - Use the run_mongodb_query tool to execute the mongodb nosql generated query.
                - After running the query, analyze and summarize the results in clear, concise natural language for the user.
            """
        )

        # Add context to the prompt if provided
        user_prompt = request.prompt

        # Collect complete response
        full_response = ""

        agent_stream = agent.stream_async(user_prompt)
        async for event in agent_stream:
            if "data" in event:
                full_response += event["data"]

        return {
            "answer": full_response.strip(),
            "prompt": request.prompt,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in agent_response_sync: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
