from dataclasses import dataclass
from datetime import timedelta
from typing import List
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import async_timeout
import logging

from .aula_proxy.models.module import (
    AulaChildProfile,
    AulaDailyOverview,
    AulaMessageThread,
    AulaProfile,
)
from .aula_client import AulaClient
from .aula_proxy.aula_errors import AulaCredentialError

_LOGGER = logging.getLogger(__name__)

@dataclass
class AulaDataCoordinatorData:
    device_id: str
    aula_version: int
    profiles: List[AulaProfile]
    children: List[AulaChildProfile]
    daily_overviews: List[AulaDailyOverview]
    message_threads: List[AulaMessageThread]

class AulaDataCoordinator(DataUpdateCoordinator[AulaDataCoordinatorData]):
    """My custom coordinator."""

    _client: AulaClient

    def __init__(self, device_id: str, hass: HomeAssistant, client: AulaClient):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="general",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(minutes=5),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True
        )
        self._client = client
        self.device_id = device_id
        self.aula_version = client.aula_version

        _LOGGER.debug(f"Coordinator {device_id} initialized")

    async def _async_setup(self) -> None:
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.

        If the refresh fails, async_config_entry_first_refresh will
        raise ConfigEntryNotReady and setup will try again later
        """
        await self.hass.async_add_executor_job(self._connection_check)

    async def _async_update_data(self) -> AulaDataCoordinatorData:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:

            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_idx = set(self.async_contexts())

                # always retrieve profiles first
                data = await self.hass.async_add_executor_job(self._fetch_data)
                if isinstance(data, Exception):
                    raise data
                return data
        except AulaCredentialError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as error:
            if isinstance(error.args, str):
                raise UpdateFailed(error.args)
            else:
                raise UpdateFailed(error)

    def _connection_check(self) -> Exception | None:
        return self._client.connection_check()

    def _fetch_data(self) -> AulaDataCoordinatorData|Exception:
        try:
            logindata = self._client.login()
            profiles = logindata.profiles
            self.aula_version = logindata.api_version
            daily_overviews = self._client.get_daily_overviews(profiles)
            message_threads = self._client.get_message_threads(profiles)
            data = AulaDataCoordinatorData(
                device_id = self.device_id,
                aula_version = self.aula_version,
                profiles = profiles,
                children = [child for profile in profiles for child in profile.children],
                daily_overviews = daily_overviews,
                message_threads = message_threads
            )
        except Exception as ex:
            _LOGGER.error(ex)
            return ex
        # _LOGGER.debug(f"Coordinator fetched data: {data)")
        return data