import aiohttp

from custom_components.optispark.configuration_service import ConfigurationService, config_service


class ThermostatService:

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._config_service: ConfigurationService = config_service
        self._base_url = config_service.get("backend.baseUrl")

    async def get_control(self, thermostat_id: int):
        endpoint = config_service.get("backend.thermostat.control")
        thermostat_url = f'{self._base_url}/{endpoint}'.replace("{thermostat_id}", str(thermostat_id))
        print(thermostat_url)
        return None