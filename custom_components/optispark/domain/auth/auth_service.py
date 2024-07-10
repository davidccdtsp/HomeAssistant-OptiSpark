from http import HTTPStatus

import aiohttp

from custom_components.optispark.configuration_service import ConfigurationService
from custom_components.optispark.domain.auth.model.login_response import LoginResponse
from custom_components.optispark.domain.exception.exceptions import OptisparkApiClientAuthenticationError


class AuthService:

    _config_service: ConfigurationService

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._config_service = ConfigurationService(config_file="./config/config.json")

    async def login(self, user_hash: str) -> LoginResponse:
        auth_url = self._config_service.get("backend.baseUrl")
        try:
            payload = {"user_hash": user_hash}
            response = await self._session.request(
                method="post",
                url=auth_url,
                json=payload,
            )

            if response.status != HTTPStatus.OK:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            json_response = await response.json()

            return LoginResponse(
                token=json_response["accessToken"],
                token_type=json_response["tokenType"],
                has_locations=json_response["hasLocations"],
                has_devices=json_response["hasDevices"],
            )

        except:
            raise OptisparkApiClientAuthenticationError(
                "Invalid credentials",
            ) from Exception