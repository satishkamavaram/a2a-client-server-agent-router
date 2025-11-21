from datetime import datetime
from typing import Any, Union, Optional
from keycloak import KeycloakOpenID
from ai_app.exceptions.exception import AIException
from ai_app.logger.log_config import get_outbound_access_logger
from ai_app.utils.utils import (
    replace_newline_with_space,
)

outbound_access_logger = get_outbound_access_logger()


class Keycloak:

    def __init__(
        self,
        keycloak_server: str,
        keycloak_client_id: str,
        keycloak_realm: str,
        client_secret_key: Optional[str] = None,
        connect_timeout: Optional[int] = 60,
    ):

        self.keycloak_server = keycloak_server
        self.keycloak_client_id = keycloak_client_id
        self.keycloak_realm = keycloak_realm
        self.client_secret_key = client_secret_key
        self.connect_timeout = connect_timeout

    async def __get_keycloak(self):

        return KeycloakOpenID(
            server_url=self.keycloak_server,
            client_id=self.keycloak_client_id,
            realm_name=self.keycloak_realm,
            client_secret_key=self.client_secret_key,
            timeout=self.connect_timeout,
        )

    async def async_get_token(self, user: str, password: str) -> Union[Any, None]:
        try:
            end_time = 0
            elapsed_time = 0
            keycloak_openid = None
            response_status = "s:200"
            start_time = datetime.now()
            if user and password:
                keycloak_openid = await self.__get_keycloak()
                res = await keycloak_openid.a_token(user, password)
                print(f"Token response: {res}")
                return res
            else:
                e = "Invalid user credentials"
                response_status = f"f:{e}"
                raise AIException(f"Authentication failed:", e)
        except Exception as e:
            error_message = replace_newline_with_space(str(e))
            response_status = f"f:{error_message}"
            raise AIException(f"Failed to get Keycloak token:", e)
        finally:
            end_time = datetime.now()
            elapsed_time = round((end_time - start_time).total_seconds())
            outbound_access_logger.info(
                f"POST /async_get_token {response_status} {elapsed_time}"
            )

    async def async_decode_token(self, token: str) -> Union[Any, None]:
        try:
            end_time = 0
            elapsed_time = 0
            keycloak_openid = None
            start_time = datetime.now()
            response_status = "s:200"
            if token:
                keycloak_openid = await self.__get_keycloak()
                token_info = await keycloak_openid.a_decode_token(
                    token,
                    validate=True,
                )
                print(f"TokenInfo response: {token_info}")
                return token_info
            else:
                e = "Invalid token"
                response_status = f"f:{e}"
                raise AIException(f"Failed to retrieve token info", e)
        except Exception as e:
            error_message = replace_newline_with_space(str(e))
            response_status = f"f:{error_message}"
            raise AIException(f"Failed to decode keycloak token:", e)
        finally:
            end_time = datetime.now()
            elapsed_time = round((end_time - start_time).total_seconds())
            outbound_access_logger.info(
                f"POST /async_decode_token {response_status} {elapsed_time}"
            )