"""The CollectShine integration: a record shelf that can be asked for a record."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CollectShineClient
from .coordinator import CollectShineConfigEntry, CollectShineCoordinator
from .intent import async_setup_intents

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: CollectShineConfigEntry) -> bool:
    client = CollectShineClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_TOKEN],
    )

    coordinator = CollectShineCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Registered once for the integration rather than per entry: an intent has no way to name
    # which base station it means, and registering the same intent twice would replace the first.
    await async_setup_intents(hass)

    entry.async_on_unload(entry.add_update_listener(_reload_on_options_change))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: CollectShineConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _reload_on_options_change(hass: HomeAssistant, entry: CollectShineConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
