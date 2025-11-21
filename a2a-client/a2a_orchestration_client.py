import asyncio
import json
from typing import Any
from uuid import uuid4
import httpx
from a2a.client import A2AClient
from a2a.client import A2ACardResolver
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,

)
from a2a.types import (
    MessageSendParams,
)


def get_user_query() -> str:
    return input('\nUser Query:  ')


# formatted resposne from agent server
# context_id should be same like sessionId for entire converation
"""{
  "id": "8f4a0e22183347098f5ea9a63e07d9f1",
  "jsonrpc": "2.0",
  "result": {
    "task": {
      "id": "30818a99-5ca7-4983-aaf2-ef000c6d5e36",
      "kind": "task",
      "context_id": "06e0dd6afc4b4177a98e1cbdaae6461b",
      "status": {
        "state": "completed",
        "message": null,
        "timestamp": null
      },
      "artifacts": [
        {
          "artifact_id": "c9f63a1b-4e57-4512-8043-3e55bf640640",
          "name": "current_result",
          "description": "Result of request to agent.",
          "parts": [
            {
              "type": "text",
              "text": "There is a Severe Thunderstorm Warning for the BA state. A severe thunderstorm is approaching your area, and it is advised to take cover immediately."
            }
          ]
        }
      ],
      "history": [
        {
          "message_id": "b7a514afb2e8480b935aeaf673510267",
          "role": "user",
          "text": "BA state"
        },
        { "message_id": "df5f3dff-a060-43fd-9764-f0d4142a8ad9", "role": "agent", "text": "Processing your request" },
        { "message_id": "e91516e7-0fa9-4917-ad67-53f0654e046d", "role": "agent", "text": "Processing your request" },
        { "message_id": "4b94ea35-8fa6-4717-888d-8c06b69b2cab", "role": "agent", "text": "Processing your request" },
        { "message_id": "9a704a3d-f595-4cbf-957c-79519e1d75f0", "role": "agent", "text": "Processing your request" },
        { "message_id": "5035354b-8b86-4436-aff5-1981e355b4f9", "role": "agent", "text": "Processing your request" },
        { "message_id": "178d4068-ca47-416f-9108-3f6ae3c85a4e", "role": "agent", "text": "Processing your request" }
      ]
    }
  }
}"""


async def interact_with_server(client: A2AClient) -> None:
    last_context_id: str | None = uuid4().hex
    while True:
        user_input = get_user_query()
        if user_input.lower() == 'exit':
            print('Thank You for experimenting A2A jira agent')
            break
        print("last_context_id::::", last_context_id)
        # message received on server = context.message: context_id='2adeea47b2294d77ad4a65b7e5670869' extensions=None kind='message' message_id='691f814614c44365bf1c02ff44353721' metadata=None parts=[Part(root=TextPart(kind='text', metadata=None, text='BAYERN'))] reference_task_ids=None role=<Role.user: 'user'> task_id='52a13d95-a6c9-40df-b764-4e0ec89cd22a'
        # message response: root=SendMessageSuccessResponse(id='8f4a0e22183347098f5ea9a63e07d9f1', jsonrpc='2.0', result=Task(artifacts=[Artifact(artifact_id='c9f63a1b-4e57-4512-8043-3e55bf640640', description='Result of request to agent.', extensions=None, metadata=None, name='current_result', parts=[Part(root=TextPart(kind='text', metadata=None, text='There is a Severe Thunderstorm Warning for the BA state. A severe thunderstorm is approaching your area, and it is advised to take cover immediately.'))])], context_id='06e0dd6afc4b4177a98e1cbdaae6461b', history=[Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='b7a514afb2e8480b935aeaf673510267', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='BA state'))], reference_task_ids=None, role=<Role.user: 'user'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36'), Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='df5f3dff-a060-43fd-9764-f0d4142a8ad9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Processing your request'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36'), Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='e91516e7-0fa9-4917-ad67-53f0654e046d', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Processing your request'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36'), Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='4b94ea35-8fa6-4717-888d-8c06b69b2cab', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Processing your request'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36'), Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='9a704a3d-f595-4cbf-957c-79519e1d75f0', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Processing your request'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36'), Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='5035354b-8b86-4436-aff5-1981e355b4f9', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Processing your request'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36'), Message(context_id='06e0dd6afc4b4177a98e1cbdaae6461b', extensions=None, kind='message', message_id='178d4068-ca47-416f-9108-3f6ae3c85a4e', metadata=None, parts=[Part(root=TextPart(kind='text', metadata=None, text='Processing your request'))], reference_task_ids=None, role=<Role.agent: 'agent'>, task_id='30818a99-5ca7-4983-aaf2-ef000c6d5e36')], id='30818a99-5ca7-4983-aaf2-ef000c6d5e36', kind='task', metadata=None, status=TaskStatus(message=None, state=<TaskState.completed: 'completed'>, timestamp=None)))

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': user_input}],
                'message_id': uuid4().hex,
                'metadata': {
                    'max_tokens': 100
                }
            },
        }

        if last_context_id:
            send_message_payload['message']['context_id'] = last_context_id
        try:
            message_request = SendMessageRequest(
                id=uuid4().hex,
                params=MessageSendParams(**send_message_payload)
            )

            print("Request payload JSON:")
            print(json.dumps(send_message_payload, indent=2, ensure_ascii=False))

            send_response: SendMessageResponse = await client.send_message(message_request)
            # Pretty-print JSON response for logs
            try:
                resp_json = send_response.model_dump(
                    mode='json', exclude_none=True)  # Pydantic v2
            except Exception:
                try:
                    root_obj = getattr(send_response, "root", send_response)
                    if hasattr(root_obj, "model_dump"):
                        resp_json = root_obj.model_dump(
                            mode='json', exclude_none=True)
                    elif hasattr(root_obj, "dict"):
                        resp_json = root_obj.dict(
                            exclude_none=True)  # Pydantic v1
                    else:
                        # Last-resort: generic serializer
                        resp_json = json.loads(json.dumps(
                            root_obj, default=lambda o: getattr(o, "__dict__", str(o))))
                except Exception:
                    resp_json = {"raw": str(send_response)}

            print("Response from jira agent (JSON):")
            print(json.dumps(resp_json, indent=2, ensure_ascii=False))
            # Unwrap RootModel if present
            root = getattr(send_response, "root", send_response)

            # Success shape: has .result (Task)
            if hasattr(root, "result") and root.result is not None:
                task = root.result
                last_context_id = task.context_id  # continue same thread next turn

                # Optional: print useful IDs
                task_id = getattr(task, "id", None)
                artifact = task.artifacts[0] if getattr(
                    task, "artifacts", []) else None
                # Extract final text defensively
                final_text = None
                if artifact and getattr(artifact, "parts", []):
                    part = artifact.parts[0]
                    final_text = getattr(part, "text", None) or getattr(
                        getattr(part, "root", None), "text", None)

                print(f"context_id={last_context_id}, task_id={task_id}")
                if final_text:
                    print(f"Answer: \n{final_text}")

        # formatted response from agent server.

        except Exception as e:
            print(f'An error occurred: {e}')


async def main() -> None:
    print('Welcome to the A2A client!')
    print("Please enter your query (type 'exit' to quit):")
    headers = {"Authorization": "Bearer satish_token_a2a_2"}
    async with httpx.AsyncClient(timeout=30, headers=headers) as httpx_client:
        card_resolver = A2ACardResolver(
            httpx_client, 'http://localhost:10001'  # connecting to jira agent server
        )
        card = await card_resolver.get_agent_card()
        print(f"Resolved db agent card: {card}")
        # client = httpx.AsyncClient(timeout=30)
        a2a_client = A2AClient(
            httpx_client, card, url='http://localhost:10001'
        )
        await interact_with_server(a2a_client)


if __name__ == '__main__':
    asyncio.run(main())
