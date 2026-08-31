"""Polling coordinator for a CollectShine base station."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    BaseStationState,
    CannotConnect,
    CollectShineClient,
    InvalidAuth,
    SubscriptionRequired,
    UnsupportedVersion,
)
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type CollectShineConfigEntry = ConfigEntry[CollectShineCoordinator]


class CollectShineCoordinator(DataUpdateCoordinator[BaseStationState]):
    """Holds one base station's state, refreshed on a timer.

    Every entity reads from here and none of them polls on its own. The base station composes the
    whole picture into a single endpoint precisely so that a handful of entities does not become a
    handful of requests to a Raspberry Pi every thirty seconds.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CollectShineConfigEntry,
        client: CollectShineClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> BaseStationState:
        try:
            return await self.client.state()
        except InvalidAuth as err:
            # Raised rather than logged: the owner revoked this token in the CollectShine app, and
            # ConfigEntryAuthFailed is what turns that into a repair card asking for a new one
            # instead of an integration that has quietly stopped working.
            raise ConfigEntryAuthFailed(str(err)) from err
        except SubscriptionRequired as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (CannotConnect, UnsupportedVersion) as err:
            raise UpdateFailed(str(err)) from err
