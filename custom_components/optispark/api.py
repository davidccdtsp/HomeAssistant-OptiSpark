"""Optispark API Client."""

from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout
from decimal import Decimal
from datetime import datetime, timezone
import pickle
import gzip
import base64

from homeassistant.core import async_get_hass, HomeAssistant

from .configuration_service import ConfigurationService, config_service
from .const import LOGGER, TARIFF_PRODUCT_CODE, TARIFF_CODE
import traceback
from http import HTTPStatus

from .domain.value_object.address import Address
from .domain.value_object.control_info import ControlInfo
from .infra.auth.auth_service import AuthService
from .infra.auth.model.login_response import LoginResponse
from .infra.device.device_service import DeviceService
from .infra.device.model.device_request import DeviceRequest
from .infra.device.model.device_response import DeviceResponse
from .infra.exception.exceptions import *
from .infra.location.location_service import LocationService
from .infra.location.model.location_request import (
    LocationRequest,
)
from .infra.location.model.location_response import LocationResponse

import time
import pytz

from .infra.shared.model.working_mode import WorkingMode
from .infra.thermostat.model.thermostat_control_request import ThermostatControlRequest
from .infra.thermostat.model.thermostat_control_response import ThermostatControlResponse
from .infra.thermostat.model.thermostat_control_status import ThermostatControlStatus
from .infra.thermostat.thermostat_service import ThermostatService

# class OptisparkApiClientError(Exception):
#     """Exception to indicate a general API error."""


# class OptisparkApiClientTimeoutError(OptisparkApiClientError):
#     """Lamba probably took too long starting up."""


# class OptisparkApiClientCommunicationError(OptisparkApiClientError):
#     """Exception to indicate a communication error."""
#
#
# class OptisparkApiClientAuthenticationError(OptisparkApiClientError):
#     """Exception to indicate an authentication error."""
#
#
# class OptisparkApiClientLambdaError(OptisparkApiClientError):
#     """Exception to indicate lambda return an error."""
#
#
# class OptisparkApiClientPostcodeError(OptisparkApiClientError):
#     """Exception to indicate invalid postcode."""
#
#
# class OptisparkApiClientUnitError(OptisparkApiClientError):
#     """Exception to indicate unit error."""

BACKEND_URL = 'backend.url'


def floats_to_decimal(obj):
    """Convert data types to those supported by DynamoDB."""
    # Base cases
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, str):
        return obj
    elif obj is None:
        return None
    # Go deeper
    elif isinstance(obj, dict):
        return {
            floats_to_decimal(key): floats_to_decimal(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, set):
        return {floats_to_decimal(element) for element in obj}
    elif isinstance(obj, list):
        return [floats_to_decimal(element) for element in obj]
    elif isinstance(obj, tuple):
        return (floats_to_decimal(element) for element in obj)
    elif isinstance(obj, datetime):
        return floats_to_decimal(obj.timestamp())
    else:
        LOGGER.error(f"Object of type {type(obj)} not supported by DynamoDB")
        raise TypeError(f"Object of type {type(obj)} not supported by DynamoDB")


class OptisparkApiClient:
    """Optispark API Client."""

    _token: str | None
    _user_hash: str
    _has_locations: bool
    _has_devices: bool
    _address: Address
    _auth_service: AuthService
    _location_service: LocationService
    _config_service: ConfigurationService

    def __init__(
            self,
            session: aiohttp.ClientSession,
            user_hash: str,
            address: Address
    ) -> None:
        """Sample API Client."""
        self._session = session
        self._user_hash = user_hash
        self._address = address
        self._token = None
        self._has_locations = False
        self._has_devices = False
        self._auth_service = AuthService(session=session)
        self._location_service = LocationService(session=session)
        self._device_service = DeviceService(session=session)
        self._thermostat_service = ThermostatService(session=session)
        # self._config_service = ConfigurationService(config_file='./config/config.json')
        self._config_service: ConfigurationService = config_service

    def datetime_set_utc(self, d: dict[str, datetime]):
        """Set the timezone of the datetime values to UTC."""
        for key in d:
            if d[key] is None:
                continue
            d[key] = d[key].replace(tzinfo=timezone.utc)
        return d

    async def upload_history(self, dynamo_data):
        """Upload historical data to dynamoDB without calculating heat pump profile."""
        url = self._config_service.get(BACKEND_URL)
        payload = {"dynamo_data": dynamo_data}
        payload["upload_only"] = True
        extra = await self._api_wrapper(
            method="post",
            url=url,
            data=payload,
        )
        oldest_dates = self.datetime_set_utc(extra["oldest_dates"])
        newest_dates = self.datetime_set_utc(extra["newest_dates"])
        return oldest_dates, newest_dates

    # async def check_and_set_manual(self, data: dict):

    async def check_and_set_manual(self, data: ControlInfo) -> bool:
        """Checks if optispark is running in manual, if not set manual mode"""

        control = await self.get_thermostat_control()
        if not control.status == ThermostatControlStatus.MANUAL:
            LOGGER.debug(f'Control in {control.status} status, requesting manual change...')
            print(f' {control.status} --> generating manual control request')
            manual_control = await self.create_manual(
                thermostat_id=control.thermostat_id,
                set_point=data.set_point,
                mode=data.mode
            )
            print(f'Created: {manual_control.status} - {manual_control.mode} - {manual_control.heat_set_point} -/'
                  f' {manual_control.cool_set_point}')
            return manual_control.status == ThermostatControlStatus.MANUAL


    async def get_data_dates(self, dynamo_data: dict):
        """Call lambda and only get the newest and oldest dates in dynamo.

        dynamo_data will only contain the user_hash.
        """
        print("--------------------------")
        # 3f009bbd4f13f05061d40e980c86e817c60835017a152d3bf3efa089196665d9
        print(dynamo_data["user_hash"])
        control = await self.get_thermostat_control()
        if not control.status == ThermostatControlStatus.MANUAL:
            LOGGER.debug(f'Control in {control.status} status, requesting manual')
            print(f' {control.status} --> generating manual control request')
            manual_control = await self.create_manual(
                thermostat_id=control.thermostat_id,
                set_point=dynamo_data["temp_set_point"],
                mode=dynamo_data["heat_pump_mode_raw"]
            )
            print(f'Created: {manual_control.status} - {manual_control.mode} - {manual_control.heat_set_point} -/'
                  f' {manual_control.cool_set_point}')

        tz = pytz.timezone("Europe/London")
        todays_time = time.time()
        current = datetime.fromtimestamp(timestamp=todays_time, tz=tz)
        # yesterday = current - datetime.date.timedelta(days=1)
        yesterday = datetime(year=2024, month=6, day=8)

        extra = {
            "oldest_dates": {
                "heat_pump_power": yesterday,
                "external_temperature": yesterday,
                "climate_entity": yesterday,
            },
            "newest_dates": {
                "heat_pump_power": current,
                "external_temperature": current,
                "climate_entity": current,
            },
        }

        oldest_dates = self.datetime_set_utc(extra["oldest_dates"])
        newest_dates = self.datetime_set_utc(extra["newest_dates"])

        return oldest_dates, newest_dates

    async def async_get_profile(self, lambda_args: dict):
        """Get heat pump profile only."""
        # lambda_url = 'https://lhyj2mknjfmatuwzkxn4uuczrq0fbsbd.lambda-url.eu-west-2.on.aws/'
        # lambda_url = "http://localhost:5000/home-assistant/profile"
        # url = self._config_service.get(BACKEND_URL)
        #
        # payload = lambda_args
        # payload["get_profile_only"] = True
        # LOGGER.debug("----------Lambda get profile----------")
        # results, errors = await self._api_wrapper(
        #     method="post",
        #     url=url,
        #     data=payload,
        # )
        # if errors["success"] is False:
        #     LOGGER.debug(f'OptisparkApiClientLambdaError: {errors["error_message"]}')
        #     raise OptisparkApiClientLambdaError(errors["error_message"])
        # if results["optimised_cost"] == 0:
        #     # Heating isn't active.  Should the savings be 0?
        #     results["projected_percent_savings"] = 100
        # else:
        #     results["projected_percent_savings"] = (
        #         results["base_cost"] / results["optimised_cost"] * 100 - 100
        #     )
        # return results

        payload = lambda_args
        payload["get_profile_only"] = True
        print(lambda_args)
        LOGGER.debug("----------Lambda get profile----------")
        tz = pytz.timezone("Europe/London")
        todays_time = time.time()
        current = datetime.fromtimestamp(timestamp=todays_time, tz=tz)

        results = {
            "timestamp": [current],
            "electricity_price": [10],
            "base_power": [15],
            "optimised_power": [10],
            "optimised_internal_temp": [17],
            "external_temp": [15],
            "temp_controls": [2],
            "dni": [10],
            "total_cost_optimised": 1.3,
            "base_cost": 1.0,
            "optimised_cost": 2.0,
        }

        if results["optimised_cost"] == 0:
            # Heating isn't active.  Should the savings be 0?
            results["projected_percent_savings"] = 100
        else:
            results["projected_percent_savings"] = (
                    results["base_cost"] / results["optimised_cost"] * 100 - 100
            )
        return results

    async def get_thermostat_control(self) -> ThermostatControlResponse:
        print('get working mode')
        if not self._token:
            await self._login()

        locations = await self._location_service.get_locations(self._token)
        if locations[0]:
            thermostat_id = locations[0].thermostat_id
            LOGGER.debug(f'Getting thermostat control mode')
            control = await self._thermostat_service.get_control(thermostat_id=thermostat_id, access_token=self._token)
            print(f'thermostat id: {control.thermostat_id}')
            print(f'mode: {control.mode}')
            print(f'status: {control.status}')
            return control

    async def create_manual(self, thermostat_id: int, set_point: float, mode: str) -> ThermostatControlResponse:
        request = ThermostatControlRequest(
            mode=WorkingMode.from_string(mode),
            heat_set_point=set_point,
            cool_set_point=set_point
        )
        result = await self._thermostat_service.create_manual(
            thermostat_id=thermostat_id,
            request=request,
            access_token=self._token
        )
        return result

    def json_serialisable(self, data):
        """Convert to compressed bytes so that data can be converted to json."""
        uncompressed_data = pickle.dumps(data)
        # print(data)
        # print(uncompressed_data)
        compressed_data = gzip.compress(uncompressed_data)
        LOGGER.debug(f"len(uncompressed_data): {len(uncompressed_data)}")
        LOGGER.debug(f"len(compressed_data): {len(compressed_data)}")
        base64_string = base64.b64encode(compressed_data).decode("utf-8")
        return base64_string

    def json_deserialise(self, payload):
        """Convert from the compressed bytes to original objects."""
        # payload = payload["serialised_payload"]
        # payload = payload["serialisePayload"]
        payload = base64.b64decode(payload)
        payload = gzip.decompress(payload)
        payload = pickle.loads(payload)
        return payload

    async def _api_wrapper(self, method: str, url: str, data: dict):
        """Call the Lambda function."""

        if not self._token:
            # If user is not logged perform login process
            await self._login()

        try:
            if "dynamo_data" in data:
                data["dynamo_data"] = floats_to_decimal(data["dynamo_data"])
            data_serialised = self.json_serialisable(data)

            async with async_timeout.timeout(120):
                await self._login(data)

                response = await self._session.request(
                    method=method,
                    url=url,
                    json=data_serialised,
                )
                if response.status in (401, 403):
                    # Clean token forcing login in next api_wrapper call
                    self._token = None
                    raise OptisparkApiClientAuthenticationError(
                        "Invalid credentials",
                    )

                if response.status == 502:
                    # HomeAssistant will not print errors if there was never a successful update
                    LOGGER.debug(
                        "OptisparkApiClientCommunicationError:\n  502 Bad Gateway - check payload"
                    )
                    raise OptisparkApiClientCommunicationError(
                        "502 Bad Gateway - check payload"
                    )
                response.raise_for_status()
                payload = await response.json()
                return self.json_deserialise(payload)

        except asyncio.TimeoutError as exception:
            LOGGER.error(traceback.format_exc())
            LOGGER.error(
                "OptisparkApiClientTimeoutError:\n  Timeout error fetching information"
            )
            raise OptisparkApiClientTimeoutError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            LOGGER.error(traceback.format_exc())
            LOGGER.error(
                "OptisparkApiClientCommunicationError:\n  Error fetching information"
            )
            raise OptisparkApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            LOGGER.error(traceback.format_exc())
            LOGGER.error("OptisparkApiClientError:\n  Something really wrong happened!")
            raise OptisparkApiClientError(
                "Something really wrong happened!"
            ) from exception

    async def _login(self):
        """
        Makes home asssistant login into OptiSpark backend.
        checks if user has locations and devices
        if not create locataion and device
         """
        LOGGER.debug(f" Initiating login into OptiSpark backend")
        location: LocationResponse | None = None
        if not self._token:
            # user_hash = data["user_hash"]
            if self._user_hash:
                loginResponse: LoginResponse = await self._auth_service.login(
                    user_hash=self._user_hash
                )
                self._token = loginResponse.token
                self._has_locations = loginResponse.has_locations
                self._has_devices = loginResponse.has_devices
                LOGGER.debug(f" User token: {loginResponse.token}")
        if not self._has_locations:
            location_request = LocationRequest(
                name="home",
                address=self._address.address,
                zipcode=self._address.postcode,
                city=self._address.city,
                country=self._address.country,
                tariff_id=1,
                tariff_params={
                    "product_code": TARIFF_PRODUCT_CODE,
                    "tariff_code": TARIFF_CODE,
                }
            )
            location: LocationResponse | None = await self._location_service.add_location(
                request=location_request,
                access_token=self._token
            )
            self._has_locations = True if location else False
        if not self._has_devices:
            if not location:
                locations: [LocationResponse] = await self._location_service.get_locations(access_token=self._token)
                location = locations[0]

            device_request = DeviceRequest(
                name='Heat Pump',
                location_id=location.id,
                manufacturer='ha',
                model_name='ha_model',
                version='version',
                integration_params={}
            )
            device_response: DeviceResponse | None = await self._device_service.add_device(
                request=device_request,
                access_token=self._token
            )

            self._has_devices = True if device_response else False
