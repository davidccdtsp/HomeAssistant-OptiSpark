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

        async def get_control(self, thermostat_id: int):
            return None