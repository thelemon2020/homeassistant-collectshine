"""The CollectShine integration: a record shelf that can be asked for a record."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CollectShineClient
from .coordinator import CollectShineConfigEntry, CollectShineCoordinator
from .intent import async_setup_intents
from .onboarding import async_prompt_for_sentences

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

    # The options this setup is running with. An update listener fires on any change to the
    # entry, including the bookkeeping write below and the token swap a reauth makes — and
    # reauth reloads on its own, so reloading again here would do it twice.
    setup_options = dict(entry.options)

    async def _reload_on_options_change(hass: HomeAssistant, updated: CollectShineConfigEntry) -> None:
        if dict(updated.options) == setup_options:
            return

        await hass.config_entries.async_reload(updated.entry_id)

    entry.async_on_unload(entry.add_update_listener(_reload_on_options_change))

    # Last, because it writes to the entry: everything above should already be working by the
    # time the owner is invited to go and talk to it.
    await async_prompt_for_sentences(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: CollectShineConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
