from http import HTTPStatus

import aiohttp
import jwt
import time

from custom_components.optispark.const import LOGGER
from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.infra.auth.model.login_response import LoginResponse
from custom_components.optispark.infra.exception.exceptions import OptisparkApiClientAuthenticationError


class AuthService:

    def __init__(
            self,
            session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._base_url = config_service.get('backend.baseUrl')
        self._ssl = config_service.get('backend.verifySSL', default=True)
        self._token = None

    async def login(self, user_hash: str) -> LoginResponse:
        auth_url = f'{self._base_url}/auth/ha_login'
        try:
            payload = {"user_hash": user_hash}
            response = await self._session.post(
                url=auth_url,
                json=payload,
                ssl=self._ssl
            )

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            json_response = await response.json()
            self._token = json_response["accessToken"]

            return LoginResponse(
                token=json_response["accessToken"],
                token_type=json_response["tokenType"],
                has_locations=json_response["hasLocations"],
                has_devices=json_response["hasDevices"],
            )

        except aiohttp.ClientError as e:
            LOGGER.error(f"HTTP error occurred: {e}")
            raise OptisparkApiClientAuthenticationError(
                "Invalid credentials",
            ) from e
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred: {e}")
            raise

    def is_token_expired(self):
        try:
            # Decodificar el payload del token JWT sin verificar la firma
            payload = jwt.decode(self._token, options={"verify_signature": False})
            exp_timestamp = payload.get('exp', 0)
            current_timestamp = time.time()
            return current_timestamp > exp_timestamp
        except jwt.ExpiredSignatureError:
            return True
        except jwt.DecodeError:
            return True
