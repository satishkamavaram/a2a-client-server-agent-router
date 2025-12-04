# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import logging
import uuid

from collections.abc import AsyncIterable
from typing import Any, Literal, Dict

from pydantic import BaseModel
from dotenv import load_dotenv
from strands.models.litellm import LiteLLMModel
from strands import Agent, tool
import os

from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from context_vars import get_access_token
from redis_semantic_cache import get_cache
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.environ.get('OPENAI_API_KEY').strip()
mcp_server_url = os.environ.get('MCP_SERVER_URL').strip()
redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
cache = get_cache()


def extract_tool_info(event):
    """
    Extract tool names and arguments from agent event

    Args:
        event: The event dictionary from the agent stream

    Returns:
        list: List of dictionaries containing tool info
    """
    tool_calls = []

    try:
        if 'message' in event:
            message = event['message']
            if 'content' in message and isinstance(message['content'], list):
                for content_item in message['content']:
                    if 'toolUse' in content_item:
                        tool_use = content_item['toolUse']
                        tool_info = {
                            'toolUseId': tool_use.get('toolUseId'),
                            'name': tool_use.get('name'),
                            'input': tool_use.get('input', {})
                        }
                        tool_calls.append(tool_info)
    except Exception as e:
        print(f"Error extracting tool info: {e}")

    return tool_calls


class JiraAgent:

    def __init__(self):
        print(":::::::api_key::::", api_key)
        self.model = LiteLLMModel(
            client_args={
                "api_key": api_key,
                # "api_base": None,
                "base_url": None,
                #  "use_litellm_proxy": False,
            },
            # **model_config
            model_id="openai/gpt-4o",
            params={
                "max_tokens": 500,
                "temperature": 0.7,
            }
        )
        self.agent = None
        self._initialized = False
        self.map_client: dict[str, Agent] = {}

        print("::::::::::::::::::initializing agent")

    async def get_agent(self):
        token = get_access_token()
        print(":::::::token::::::::::: ", token)
        mcp_client = self.map_client.get(token)
        if mcp_client:
            print(f"mcp_client:::from cache:{mcp_client}")
        else:
            print(f"loading::::mcp_client:::")
            mcp_client = MCPClient(
                lambda: streamablehttp_client(
                    # url="http://localhost:8001/mcp",
                    url=mcp_server_url,
                    # url="http://host.docker.internal:8000/mcp",
                    # nginx with 2 mcp servers on 8000, 8001 port
                    # url="http://host.docker.internal:8888/mcp",
                    # Get pat token from here: https://github.com/settings/personal-access-tokens

                    headers={"Authorization": f"Bearer {token}"}
                )
            )
            # Enter the client context ONCE and keep it open for this txid
            try:
                entered_client = mcp_client.__enter__()
                # Some context managers return self; use whichever is returned
                mcp_client = entered_client or mcp_client
                self.map_client[token] = mcp_client
            except Exception:
                # If __enter__ is unavailable or fails, client may lazy-init; proceed
                pass

        tools = mcp_client.list_tools_sync()
        return Agent(model=self.model, tools=tools,
                     callback_handler=None)

    async def get_similarity_agent(self):
        token = get_access_token()
        print(":::::::similarity agent token::::::::::: ", token)
        prompt = """You are an agent that decides if two statements ask the same question. Output only True or False.
        Rules:
        - True if both statements ask for the same information and scope.
        - False if scope differs (e.g., deployable-only vs all), format requirements differ (e.g., tree view, by category), or constraints differ (e.g., name+version only).

        Examples:
        - Example 1 → False
        statement 1: what are dependencies of test 1.0.0
        statement 2: deployable dependencies of test version 1.0.0 list by category

        - Example 2 → True
        statement 1: what are dependencies of test 1.0.0
        statement 2: dependencies of test version 1.0.0 """
        return Agent(model=self.model, tools=[], system_prompt=prompt,
                     callback_handler=None)

    """
    Agent Flow (cache and avoid false positives)
    1. First checks similar user question is already in cache(redisVL)
    2. If similar user question not found in cache, Querying the agent to answer user question
    3. If similar user question foudn in cache, checking with similarity agent to decide if user question matches the one found in cache
       - if matches, results are returned from cache (redisVL)
       - if not matched, Querying the agent to answer user question 
    """

    async def stream(
        self, query: str, context_id: str | None = None
    ) -> AsyncIterable[dict[str, Any]]:
        logger.debug(
            f"Starting stream with query: {query} and context_id: {context_id}")
        try:
            cache_result = None
            if redis_enabled:
                cache_result = cache.get_from_cache(
                    user_question=query,
                    distance_threshold=0.5
                )
            if cache_result:
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': f'cache hit... matching question found in cache : <b>{cache_result[0]["prompt"]}</b> with similarity distance of {cache_result[0]["vector_distance"]}',
                }
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Checking if your question matches the one found in cache..',
                }
                similarity_agent = await self.get_similarity_agent()
                similarity_query = f"statement 1: {query} \n statement 1: {cache_result[0]["prompt"]}"
                agent_stream = similarity_agent.stream_async(similarity_query)
                full_response = ""
                total_tokens = 0
                async for event in agent_stream:
                    if "data" in event:
                        chunk = event["data"]
                    # print("============chunk::::", chunk)
                        full_response += chunk
                    elif 'result' in event:
                        result = event['result']
                        if hasattr(result, 'metrics') and result.metrics:
                            if hasattr(result.metrics, 'accumulated_usage') and result.metrics.accumulated_usage:
                                total_tokens = result.metrics.accumulated_usage.get(
                                    'totalTokens', 0)
                print("============Task completed=======")
                print(f"\n{total_tokens}")
                token_similarity_message = f"Total Tokens Consumed for similarity check: {total_tokens}"
                is_similar = full_response
                if "True" in is_similar:
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': "Both questions are similar. Returning results from cache.",
                    }
                    yield {
                        'is_task_complete': True,
                        'require_user_input': False,
                        'content': cache_result[0]["response"] + "\n\n" + token_similarity_message,
                    }
                    print("sending response from cache")
                    return
                else:
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': "The questions aren’t similar. Querying the agent to answer your question." + "\n\n" + token_similarity_message,
                    }

            else:
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'cache miss...Querying the agent to answer your question.',
                }

            agent = await self.get_agent()
            print("agent object received::", agent)
            # Use the context_id as the thread_id, or generate a new one if none provided

            agent_stream = agent.stream_async(query)
            full_response = ""
            total_tokens = 0
            async for event in agent_stream:
                # print("((((((((((()))))))))))", event)
                if 'message' in event:
                    tool_calls = extract_tool_info(event)
                    if tool_calls:
                        for tool in tool_calls:
                            print(
                                f"Tool called: {tool['name']} with args: {tool['input']}")
                            yield {
                                'is_task_complete': False,
                                'require_user_input': False,
                                'content': f"Executing tool: {tool['name']} with arguments {tool['input']}",
                            }
                elif "data" in event:
                    chunk = event["data"]
                # print("============chunk::::", chunk)
                    full_response += chunk
                elif 'result' in event:
                    result = event['result']
                    if hasattr(result, 'metrics') and result.metrics:
                        if hasattr(result.metrics, 'accumulated_usage') and result.metrics.accumulated_usage:
                            total_tokens = result.metrics.accumulated_usage.get(
                                'totalTokens', 0)
            print("============Task completed=======")
            print(f"\n{full_response}")
            print(f"\n{total_tokens}")
            print("storing in redis cache query and llm response")
            cache.store(
                user_question=query,
                llm_answer=full_response,
                ttl=60
            )
            token_message = f"Total Tokens Consumed: {total_tokens}"
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': full_response + "\n\n" + token_message,
            }
        except Exception as e:
            full_response = f"Error executing query: {str(e)}"
            print("============Task completed=======")
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': full_response,
            }
