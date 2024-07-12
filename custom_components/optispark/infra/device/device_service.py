from http import HTTPStatus

import aiohttp
from aiohttp import ClientResponse

from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.infra.device.model.device_request import DeviceRequest
from custom_components.optispark.infra.device.model.device_response import DeviceResponse
from custom_components.optispark.infra.exception.exceptions import OptisparkApiClientAuthenticationError, \
    OptisparkApiClientDeviceError


class DeviceService:

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._base_url = config_service.get("backend.baseUrl")
        self._ssl = config_service.get('backend.verifySSL', default=True)

    async def add_device(self, request: DeviceRequest, access_token: str) -> DeviceResponse | None:

        device_url = f'{self._base_url}{config_service.get("backend.device.base")}'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            response: ClientResponse = await self._session.post(
                url=device_url,
                headers=headers,
                json=request.payload(),
                ssl=self._ssl
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientDeviceError(
                    "Add device error",
                ) from Exception

            json_response = await response.json()
            return DeviceResponse.from_json(json_response)

        except aiohttp.ClientError as e:
            print(f"HTTP error occurred: {e}")
            raise OptisparkApiClientDeviceError("Add device error") from e
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            raise
