import aiohttp


class ElectrityService:

    def __init__(
            self,
            session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

