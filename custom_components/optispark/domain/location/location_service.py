from http import HTTPStatus

import aiohttp

from custom_components.optispark.configuration_service import config_service
from custom_components.optispark.domain.exception.exceptions import (
    OptisparkApiClientAuthenticationError,
    OptisparkApiClientLocationError,
)
from custom_components.optispark.domain.location.model.location_request import (
    LocationRequest,
)


class LocationService:
    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

    async def add_location(self, request: LocationRequest, access_token: str) -> bool:
        """Add new location"""

        base_url = config_service.get("backend.baseUrl")
        location_url = f'{base_url}{config_service.get("backend.location.base")}'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._session.request(
                method="post",
                url=location_url,
                headers=headers,
                json=request.payload(),
            )

            if response.status == HTTPStatus.UNAUTHORIZED:
                raise OptisparkApiClientAuthenticationError(
                    "Invalid credentials",
                ) from Exception

            if response.status != HTTPStatus.CREATED:
                raise OptisparkApiClientLocationError(
                    "Add location error",
                ) from Exception

            return True

        except aiohttp.ClientError as e:
            print(f"HTTP error occurred: {e}")
            raise OptisparkApiClientLocationError("Add location error") from e
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            raise
