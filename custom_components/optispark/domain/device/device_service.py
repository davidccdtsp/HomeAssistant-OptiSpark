from http import HTTPStatus

import aiohttp
from aiohttp import ClientResponse

from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.domain.device.model.device_request import DeviceRequest
from custom_components.optispark.domain.device.model.device_response import DeviceResponse
from custom_components.optispark.domain.exception.exceptions import OptisparkApiClientAuthenticationError, \
    OptisparkApiClientDeviceError


class DeviceService:

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

    async def add_device(self, request: DeviceRequest, access_token: str) -> DeviceResponse | None:
        base_url = config_service.get("backend.baseUrl")
        device_url = f'{base_url}{config_service.get("backend.device.base")}'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            response: ClientResponse = await self._session.request(
                method="post",
                url=device_url,
                headers=headers,
                json=request.payload(),
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientDeviceError(
                    "Add device error",
                ) from Exception

            jsonResponse = await response.json()
            return DeviceResponse.from_json(jsonResponse)

        except aiohttp.ClientError as e:
            print(f"HTTP error occurred: {e}")
            raise OptisparkApiClientDeviceError("Add device error") from e
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            raise
