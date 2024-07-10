from http import HTTPStatus

import aiohttp

from custom_components.optispark.configuration_service import ConfigurationService, config_service
from custom_components.optispark.domain.exception.exceptions import OptisparkApiClientAuthenticationError, \
    OptisparkApiClientThermostatError
from custom_components.optispark.domain.thermostat.model.thermostat_response import ThermostatResponse


class ThermostatService:

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._config_service: ConfigurationService = config_service
        self._base_url = config_service.get("backend.baseUrl")

    async def get_control(self, thermostat_id: int, access_token: str):
        endpoint = config_service.get("backend.thermostat.control")
        thermostat_url = f'{self._base_url}/{endpoint}'.replace("{thermostat_id}", str(thermostat_id))
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            response = await self._session.get(
                # method="get",
                url=thermostat_url,
                headers=headers,
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientThermostatError(
                    "Add location error",
                ) from Exception

            json_response = await response.json()
            return ThermostatResponse.from_json(json_response)

        except aiohttp.ClientError as e:
            print(f"HTTP error occurred: {e}")
            raise OptisparkApiClientThermostatError("get thermostat control error") from e
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            raise
