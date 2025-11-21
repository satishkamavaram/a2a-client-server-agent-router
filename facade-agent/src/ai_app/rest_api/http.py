from datetime import datetime
from requests.auth import HTTPBasicAuth
import json
import httpx
from collections.abc import Mapping
from typing import Any, Union
from ai_app.logger.log_config import get_app_logger, get_outbound_access_logger
from ai_app.exceptions.exception import AIException
from ai_app.logger.thread_local_context import get_txid
from ai_app.utils.utils import (
    get_base_url,
    is_http_success_status,
    replace_newline_with_space,
)
import functools

logger = get_app_logger()
outbound_access_logs = get_outbound_access_logger()


def log_http_requests(func):
    """
    An asynchronous decorator to log details about HTTP GET requests.
    Logs:
    - Start time
    - End time
    - Elapsed time
    - Function name
    - Endpoint (URL)
    - HTTP Method (GET/POST)
    - Response status
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        tx_id = get_txid()

        url = kwargs.get(
            "url", args[0] if args else "Unknown_URL"
        )  # Extract URL from positional or keyword arguments
        base_url = get_base_url(url)
        # Default to GET if not specified
        method = kwargs.get("method", "GET").upper()
        response = None
        # Execute the actual function
        try:
            response = await func(*args, **kwargs)
            status = "s" if is_http_success_status(
                response.status_code) else "f"
            response_status = f"{status}:{response.status_code}"
        except Exception as e:
            error_message = replace_newline_with_space(str(e))
            response_status = f"f:{error_message}"
            raise e
        finally:
            end_time = datetime.now()
            elapsed_time = round((end_time - start_time).total_seconds())
            outbound_access_logs.info(
                f"{method} {base_url} {response_status} {elapsed_time}"
            )

        return response

    return wrapper


@log_http_requests
async def async_execute_get(
    url: str,
    method="get",
    basic_auth: HTTPBasicAuth = None,
    headers: Mapping[str, str] = None,
    connection_timeout: int = 10,
    read_timeout: int = 120,
    raise_for_status: bool = True,
    params=None,
):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url=url,
                auth=basic_auth,
                headers=headers,
                timeout=(connection_timeout, read_timeout),
                params=params,
            )
            response.encoding = "utf-8"
            if raise_for_status:
                response.raise_for_status()
        except httpx.TimeoutException as timeout_err:
            raise Exception(
                f"Request timed out for url: {url} {str(timeout_err)}", timeout_err
            )
        except httpx.ConnectError as connect_err:
            raise Exception(
                f"Connnection timed out for url: {url} {str(connect_err)}", connect_err
            )
        except httpx.HTTPStatusError as status_error:
            raise Exception(
                f"HTTP Status error for url: {url} {str(status_error)}", status_error
            )
        except httpx.RequestError as http_err:
            raise Exception(
                f"HTTP Error Occurred for url: {url} {str(http_err)}", http_err
            )
        except Exception as err:
            raise Exception(f"Other HTTP Error for url: {url} {str(err)}", err)
        return response


async def async_get(
    url: str,
    basic_auth: HTTPBasicAuth = None,
    headers: Mapping[str, str] = None,
    connection_timeout: int = 10,
    read_timeout: int = 120,
    raise_for_status: bool = True,
    params=None,
) -> Union[str, Any]:
    logger.info(f"Sending GET request to url: {url}")
    response = await async_execute_get(
        url=url,
        method="get",
        basic_auth=basic_auth,
        headers=headers,
        connection_timeout=connection_timeout,
        read_timeout=read_timeout,
        raise_for_status=raise_for_status,
        params=params,
    )
    payload = response.text
    logger.info(f"Successfully received GET response for url: {url}")
    logger.debug(f"GET response payload: {payload}")
    # logger.debug(
    #    f"GET response payload: {json.dumps(payload,ensure_ascii=False)}"
    # )
    return payload


async def async_get_response_json(
    url: str,
    basic_auth: HTTPBasicAuth = None,
    headers: Mapping[str, str] = None,
    connection_timeout: int = 10,
    read_timeout: int = 120,
    raise_for_status: bool = True,
    params=None,
) -> Union[Any, None]:
    payload = await async_get(
        url,
        basic_auth,
        headers,
        connection_timeout,
        read_timeout,
        raise_for_status,
        params=params,
    )
    payload = json.loads(payload) if payload else None
    # if payload:
    #    payload_log = json.dumps(payload, ensure_ascii=False)
    #    logger.debug(f"GET response json payload: {payload_log}")
    return payload


@log_http_requests
async def async_execute_post(
    url: str,
    method="post",
    basic_auth: HTTPBasicAuth = None,
    headers: Mapping[str, str] = None,
    request_body: str = None,
    json_body=None,
    connection_timeout: int = 10,
    read_timeout: int = 120,
    raise_for_status: bool = True,
):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url=url,
                auth=basic_auth,
                data=request_body,
                json=json_body,
                headers=headers,
                timeout=(connection_timeout, read_timeout),
            )
            response.encoding = "utf-8"
            if raise_for_status:
                response.raise_for_status()
        except httpx.TimeoutException as timeout_err:
            raise Exception(
                f"Request timed out for url: {url} {str(timeout_err)}", timeout_err
            )
        except httpx.ConnectError as connect_err:
            raise Exception(
                f"Connnection timed out for url: {url} {str(connect_err)}", connect_err
            )
        except httpx.HTTPStatusError as status_error:
            raise Exception(
                f"HTTP Status error for url: {url} {str(status_error)}", status_error
            )
        except httpx.RequestError as http_err:
            raise Exception(
                f"HTTP Error Occurred for url: {url} {str(http_err)}", http_err
            )
        except Exception as err:
            raise Exception(f"Other HTTP Error for url: {url} {str(err)}", err)
        return response


async def async_post(
    url: str,
    request_body: str = None,
    json_body=None,
    basic_auth: HTTPBasicAuth = None,
    headers: Mapping[str, str] = None,
    connection_timeout: int = 10,
    read_timeout: int = 120,
    raise_for_status: bool = True,
) -> Union[str, Any]:
    logger.info(f"Sending async POST request to url: {url}")
    response = await async_execute_post(
        url=url,
        method="post",
        basic_auth=basic_auth,
        request_body=request_body,
        json_body=json_body,
        headers=headers,
        connection_timeout=connection_timeout,
        read_timeout=read_timeout,
        raise_for_status=raise_for_status,
    )
    response_payload = response.text
    logger.info(f"Successfully received async POST response for url: {url}")
    logger.debug(f"POST response payload: {response_payload}")
    return response_payload


async def async_post_response_json(
    url: str,
    request_body: str,
    json_body=None,
    basic_auth: HTTPBasicAuth = None,
    headers: Mapping[str, str] = None,
    connection_timeout: int = 10,
    read_timeout: int = 120,
    raise_for_status: bool = True,
) -> Union[Any, None]:
    payload = await async_post(
        url,
        request_body,
        json_body,
        basic_auth,
        headers,
        connection_timeout,
        read_timeout,
        raise_for_status,
    )
    payload = json.loads(payload) if payload else None
    # if payload:
    #     payload_log = json.dumps(payload, ensure_ascii=False)
    #     logger.debug(f"POST response json payload: {payload_log}")
    return payload
