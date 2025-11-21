# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import logging


from collections.abc import AsyncIterable
from typing import Any, Optional
from dotenv import load_dotenv
from strands.models.litellm import LiteLLMModel
from strands import Agent, tool
import os
import glob
from pathlib import Path

import asyncio
from uuid import uuid4
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart
import json
import traceback
from context_vars import set_access_token, clear_access_token, get_access_token

from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)


logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.environ.get('OPENAI_API_KEY').strip()

db_agent_url = os.environ.get('DB_AGENT_URL').strip()

requirement_agent_url = os.environ.get('REQUIREMENT_AGENT_URL').strip()

jira_agent_url = os.environ.get('JIRA_AGENT_URL').strip()


class OrchestrationAgent:

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
                # "max_tokens": 500,
                "temperature": 0.75,
            }
        )
        self.agent = None
        self._initialized = False
        self.agent_cache: dict[str, Agent] = {}

        print("::::::::::::::::::initializing agent")

    async def get_agent(self) -> Any:
        prompt = """
        You are a specialized agent in analyzing user request and return name of the agent.
        Only Following agent names are supported:
        - db
        - jira

        Examples for db agent:
        - top 5 customers with total number of sales with total sale amount more than 3700
        - show me largest sale happened in 2025

        Examples for jira agent:
        - jira tickets assigned to 1234
        - schedule a appointment on 4th sept 2026 at 4:30 am  from email satish.k@test.com and to these users test1@test.com test2@test.com to discuss about future of agentic AI
        - weather info of Bayern state

        Return just name of the agent . If no agent name matching, return empty value. Don't summarize or explain.

        """
        agent = Agent(model=self.model, callback_handler=None,
                      system_prompt=prompt, tools=[])
        return agent

    async def stream(
        self, query: str, context_id: str | None = None
    ) -> AsyncIterable[dict[str, Any]]:
        logger.debug(
            f"Starting stream with query: {query} and context_id: {context_id}")
        try:
            agent = await self.get_agent()

            full_response = ""
            total_tokens = 0
            agent_stream = agent.stream_async(query)
            async for event in agent_stream:
                # print("============event*****::::", event)
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
            print(f"\n{total_tokens}")
            token_message = f"Total Tokens Consumed: {total_tokens}"
            agent_name = full_response
            full_response = "Selected agent: "+agent_name
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': full_response + "\n\n" + token_message,
            }
            if "db" in agent_name:
                async for response in invoke_postres_db_agent(query):
                    yield response
            elif "jira" in agent_name:
                async for response in invoke_jira_agent(query):
                    yield response
            else:
                yield {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': f"No matching agent found for your query",
                }
        except Exception as e:
            full_response = f"Error executing query: {str(e)}"
            print("============Task completed=======")
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': full_response,
            }


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


def format_stream_event(evt: dict) -> Optional[str]:
    """Return 'status: <state or kind>\\n<text>' from an A2A stream event."""
    res = evt.get("result") or {}
    kind = res.get("kind")

    # Helper to join any text parts
    def join_text(parts):
        return "\n".join(
            p.get("text", "")
            for p in (parts or [])
            if isinstance(p, dict) and p.get("kind") == "text" and p.get("text")
        ).strip()

    if kind == "status-update":
        st = res.get("status") or {}
        state = st.get("state") or "status-update"
        msg = st.get("message") or {}
        text = join_text(msg.get("parts"))
        return f"status: {state}\n{text}" if text else f"status: {state}"

    if kind == "artifact-update":
        text = join_text((res.get("artifact") or {}).get("parts"))
        return f"status: completed\n{text}" if text else "status: artifact-update"

    if kind == "task":
        # initial submission event
        state = (res.get("status") or {}).get("state") or "submitted"
        # optionally show last history message text
        hist = res.get("history") or []
        last = hist[-1] if hist else {}
        text = join_text(last.get("parts"))
        return f"status: {state}\n{text}" if text else f"status: {state}"

    return None


async def invoke_postres_db_agent(user_input: str) -> AsyncIterable[dict[str, Any]]:
    """
    Gernerates postgres sql queries and return results for a given user input

   Args:
       user_input (str): user input

   Returns:
       Returns database results
   """
    try:
        headers = {"Authorization": f"Bearer {get_access_token()}"}
        last_context_id: str | None = uuid4().hex
        async with httpx.AsyncClient(timeout=300, headers=headers) as httpx_client:
            resolver = A2ACardResolver(
                httpx_client=httpx_client, base_url=db_agent_url)
            agent_card = await resolver.get_agent_card()

            config = ClientConfig(httpx_client=httpx_client, streaming=True)
            factory = ClientFactory(config)
            client = factory.create(agent_card)
            # send_message_payload: dict[str, Any] = {
            #    "message": {
            #        "kind": "message",
            #        "role": "user",
            #        "parts": [{"type": "text", "text": user_input}],
            #        "message_id": uuid4().hex,
            #        'metadata': {
            #            'max_tokens': 100
            #        }
            #    }
            # }
            send_message_payload = Message(
                kind="message",
                role=Role.user,
                parts=[Part(TextPart(kind="text", text=user_input))],
                message_id=uuid4().hex,
            )
           # if last_context_id:
            #    send_message_payload["message"]["context_id"] = last_context_id

            # Show outgoing payload
            try:
                print("Request payload JSON:")
                print(json.dumps(send_message_payload.model_dump(),
                                 indent=2, ensure_ascii=False))
            except Exception:
                print(f"Request payload (raw dict): {send_message_payload}")

                # Build request and start streaming
           # message_request = SendStreamingMessageRequest(
            #    id=uuid4().hex,
            #    params=MessageSendParams(**send_message_payload),
            # )
            # print(f"[send] streaming request id={message_request.id}")
            stream_response = client.send_message(
                send_message_payload)
            pre_event = None
            async for event in stream_response:
                print(event, "\n")
                line = extract_task_state_and_text(event)
                if line:
                   # print(event)
                    if pre_event:
                        yield {
                            'is_task_complete': False,
                            'require_user_input': False,
                            'content': pre_event,
                        }
                    pre_event = line
            print("\n\n")
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': pre_event,
            }
    except Exception as e:
        print(f"Error during db agent: {e}")
        print(f"Full trace:\n{traceback.format_exc()}")
        full_response = f"Error during executing db agent: {str(e)}"
        print("============Task completed=======")
        yield {
            'is_task_complete': True,
            'require_user_input': False,
            'content': full_response,
        }


async def invoke_jira_agent(user_input: str) -> AsyncIterable[dict[str, Any]]:
    try:
        last_context_id: str | None = uuid4().hex
        headers = {"Authorization": f"Bearer {get_access_token()}"}
        async with httpx.AsyncClient(timeout=300, headers=headers) as httpx_client:
            resolver = A2ACardResolver(
                httpx_client=httpx_client, base_url=jira_agent_url)
            agent_card = await resolver.get_agent_card()

            config = ClientConfig(httpx_client=httpx_client, streaming=True)
            factory = ClientFactory(config)
            client = factory.create(agent_card)
           # send_message_payload: dict[str, Any] = {
           #     "message": {
           #         "role": "user",
           #         "parts": [{"type": "text", "text": user_input}],
           #         "message_id": uuid4().hex,
           #         'metadata': {
           #             'max_tokens': 100
           #         }
           #     }
           # }
            send_message_payload = Message(
                kind="message",
                role=Role.user,
                parts=[Part(TextPart(kind="text", text=user_input))],
                message_id=uuid4().hex,
            )
            # if last_context_id:
            #    send_message_payload["message"]["context_id"] = last_context_id

            # Show outgoing payload
            try:
                print("Request payload JSON:")
                print(json.dumps(send_message_payload.model_dump(),
                                 indent=2, ensure_ascii=False))
            except Exception:
                print(f"Request payload (raw dict): {send_message_payload}")

                # Build request and start streaming
          #  message_request = SendStreamingMessageRequest(
           #     id=uuid4().hex,
           #     params=MessageSendParams(**send_message_payload),
           # )
            # print(f"[send] streaming request id={message_request.id}")
            stream_response = client.send_message(
                send_message_payload)
            pre_event = None
            async for event in stream_response:
                print(event, "\n")
                line = extract_task_state_and_text(event)
                if line:
                   # print(event)
                    if pre_event:
                        yield {
                            'is_task_complete': False,
                            'require_user_input': False,
                            'content': pre_event,
                        }
                    pre_event = line
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': pre_event,
            }
    except Exception as e:
        print(f"Error during requirement verification: {e}")
        print(f"Full trace:\n{traceback.format_exc()}")
        full_response = f"Error during executing requirement agent: {str(e)}"
        print("============Task completed=======")
        yield {
            'is_task_complete': True,
            'require_user_input': False,
            'content': full_response,
        }


def extract_task_state_and_text(task_data):
    """
    These are kinds :
     kind='task'
     kind='status-update'
     kind='artifact-update'

    kind='task'
     (Task(artifacts=None, context_id='9208944d-729a-4198-917f-cfa8dff78a3e', history=[Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='febcefad28b74cc6aab059846bc97ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='is AI-postgresdb project meeting requirements'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')], id='75550a69-98d6-4cf4-a381-b9ca7d88b619', kind='task', metadata=None, status=TaskStatus(message=None, state=<TaskState.submitted: 'submitted'>, timestamp=None)), None) 
    kind='status-update' 
     (Task(artifacts=None, context_id='9208944d-729a-4198-917f-cfa8dff78a3e', history=[Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='febcefad28b74cc6aab059846bc97ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='is AI-postgresdb project meeting requirements'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')], id='75550a69-98d6-4cf4-a381-b9ca7d88b619', kind='task', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None)), TaskStatusUpdateEvent(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', final=False, kind='status-update', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None), task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')) 
     (Task(artifacts=None, context_id='9208944d-729a-4198-917f-cfa8dff78a3e', history=[Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='febcefad28b74cc6aab059846bc97ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='is AI-postgresdb project meeting requirements'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='f62eb5e2-5ea2-45f0-9090-0db47612b320', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'Dockerfile'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')], id='75550a69-98d6-4cf4-a381-b9ca7d88b619', kind='task', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='f62eb5e2-5ea2-45f0-9090-0db47612b320', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'Dockerfile'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None)), TaskStatusUpdateEvent(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', final=False, kind='status-update', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='f62eb5e2-5ea2-45f0-9090-0db47612b320', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'Dockerfile'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None), task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')) 
     (Task(artifacts=None, context_id='9208944d-729a-4198-917f-cfa8dff78a3e', history=[Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='febcefad28b74cc6aab059846bc97ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='is AI-postgresdb project meeting requirements'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='f62eb5e2-5ea2-45f0-9090-0db47612b320', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'Dockerfile'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='3fce9b93-8faa-4d52-b26e-285e0287743c', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'gradle.properties'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')], id='75550a69-98d6-4cf4-a381-b9ca7d88b619', kind='task', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='3fce9b93-8faa-4d52-b26e-285e0287743c', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'gradle.properties'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None)), TaskStatusUpdateEvent(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', final=False, kind='status-update', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='3fce9b93-8faa-4d52-b26e-285e0287743c', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'gradle.properties'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None), task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')) 
    kind='artifact-update' 
     (Task(artifacts=[Artifact(artifact_id='b49aa7c9-922b-439d-928b-6e32c4763ad3', description='Results of agent', extensions=None, metadata=None, name='current_result', parts=[Part(root=TextPart(kind='text', metadata=None, text='| file_name      | requirement                  | status             | suggested_changes              |\n|----------------|------------------------------|--------------------|--------------------------------|\n| Dockerfile     | Container must run as a      | not implemented    | Uncomment the lines:          |\n|                | non-root user                |                    | RUN groupadd and useradd      |\n|                |                              |                    | to create non-root user       |\n| gradle.        | Version key must be semantic | not implemented    | Ensure version is in format   |\n| properties     | like major.minor.patch       |                    | major.minor.patch, e.g., 1.0.0|\n\nSummary: The AI-postgresdb project is currently not meeting the requirements as the Dockerfile does not implement the required non-root user setup, and the version in gradle.properties is not in a semantic version format.\n\nStatus: Fail\n\nTotal Tokens Consumed: 3604'))])], context_id='9208944d-729a-4198-917f-cfa8dff78a3e', history=[Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='febcefad28b74cc6aab059846bc97ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='is AI-postgresdb project meeting requirements'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='f62eb5e2-5ea2-45f0-9090-0db47612b320', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'Dockerfile'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='3fce9b93-8faa-4d52-b26e-285e0287743c', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'gradle.properties'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')], id='75550a69-98d6-4cf4-a381-b9ca7d88b619', kind='task', metadata=None, status=TaskStatus(message=Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='3fce9b93-8faa-4d52-b26e-285e0287743c', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'gradle.properties'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), state=<TaskState.working: 'working'>, timestamp=None)), TaskArtifactUpdateEvent(append=False, artifact=Artifact(artifact_id='b49aa7c9-922b-439d-928b-6e32c4763ad3', description='Results of agent', extensions=None, metadata=None, name='current_result', parts=[Part(root=TextPart(kind='text', metadata=None, text='| file_name      | requirement                  | status             | suggested_changes              |\n|----------------|------------------------------|--------------------|--------------------------------|\n| Dockerfile     | Container must run as a      | not implemented    | Uncomment the lines:          |\n|                | non-root user                |                    | RUN groupadd and useradd      |\n|                |                              |                    | to create non-root user       |\n| gradle.        | Version key must be semantic | not implemented    | Ensure version is in format   |\n| properties     | like major.minor.patch       |                    | major.minor.patch, e.g., 1.0.0|\n\nSummary: The AI-postgresdb project is currently not meeting the requirements as the Dockerfile does not implement the required non-root user setup, and the version in gradle.properties is not in a semantic version format.\n\nStatus: Fail\n\nTotal Tokens Consumed: 3604'))]), context_id='9208944d-729a-4198-917f-cfa8dff78a3e', kind='artifact-update', last_chunk=True, metadata=None, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')) 
    kind='status-update' and final 
     (Task(artifacts=[Artifact(artifact_id='b49aa7c9-922b-439d-928b-6e32c4763ad3', description='Results of agent', extensions=None, metadata=None, name='current_result', parts=[Part(root=TextPart(kind='text', metadata=None, text='| file_name      | requirement                  | status             | suggested_changes              |\n|----------------|------------------------------|--------------------|--------------------------------|\n| Dockerfile     | Container must run as a      | not implemented    | Uncomment the lines:          |\n|                | non-root user                |                    | RUN groupadd and useradd      |\n|                |                              |                    | to create non-root user       |\n| gradle.        | Version key must be semantic | not implemented    | Ensure version is in format   |\n| properties     | like major.minor.patch       |                    | major.minor.patch, e.g., 1.0.0|\n\nSummary: The AI-postgresdb project is currently not meeting the requirements as the Dockerfile does not implement the required non-root user setup, and the version in gradle.properties is not in a semantic version format.\n\nStatus: Fail\n\nTotal Tokens Consumed: 3604'))])], context_id='9208944d-729a-4198-917f-cfa8dff78a3e', history=[Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='febcefad28b74cc6aab059846bc97ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='is AI-postgresdb project meeting requirements'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='4d05824b-0268-43d2-83e3-8efaa84a78c2', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Executing tool: get_requirement with arguments {}'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='f62eb5e2-5ea2-45f0-9090-0db47612b320', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'Dockerfile'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619'), Message(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', extensions=None, kind='message', message_id='3fce9b93-8faa-4d52-b26e-285e0287743c', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text="Executing tool: extract_file_content with arguments {'repo_name': 'AI-postgresdb', 'file_names': 'gradle.properties'}"))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')], id='75550a69-98d6-4cf4-a381-b9ca7d88b619', kind='task', metadata=None, status=TaskStatus(message=None, state=<TaskState.completed: 'completed'>, timestamp=None)), TaskStatusUpdateEvent(context_id='9208944d-729a-4198-917f-cfa8dff78a3e', final=True, kind='status-update', metadata=None, status=TaskStatus(message=None, state=<TaskState.completed: 'completed'>, timestamp=None), task_id='75550a69-98d6-4cf4-a381-b9ca7d88b619')) 


    """
    """
    Extract state and text from Task object or event tuple

    Args:
        task_data: Can be:
            - Task object
            - Tuple (Task, TaskStatusUpdateEvent) 
            - Tuple (Task, TaskArtifactUpdateEvent)

    Returns:
        str: Formatted status and text information
    """
    try:
        task = None
        event = None

        # Handle different input types
        if isinstance(task_data, tuple) and len(task_data) >= 2:
            task = task_data[0]
            event = task_data[1]
        elif isinstance(task_data, tuple) and len(task_data) == 1:
            task = task_data[0]
        else:
            task = task_data

        # Extract state from task
        state = "unknown"
        if task and hasattr(task, 'status') and task.status and hasattr(task.status, 'state'):
            state = task.status.state.value

        # Check if we have an artifact event (final results)
        if event and hasattr(event, 'kind') and event.kind == 'artifact-update':
            artifact_text = ""
            if hasattr(event, 'artifact') and event.artifact and hasattr(event.artifact, 'parts'):
                for part in event.artifact.parts:
                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                        artifact_text += part.root.text

            if artifact_text.strip():
                print(f"inside artifact_text")
                return f"\n{artifact_text}"

        # Check if we have a status update event
        if event and hasattr(event, 'kind') and event.kind == 'status-update':
            if hasattr(event, 'status') and event.status:
                # Use status from the event instead of task
                if hasattr(event.status, 'state'):
                    state = event.status.state.value

                # Get message from status update event
                if hasattr(event.status, 'message') and event.status.message:
                    status_message = event.status.message
                    if hasattr(status_message, 'parts') and status_message.parts:
                        for part in status_message.parts:
                            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                print(f"inside status-update")
                                return f"status: {state}\n\n{part.root.text}"

    except Exception as e:
        print(f"Error extracting task info: {e}")
        traceback.print_exc()
        return f"status: error\nFailed to extract task information: {str(e)}"
