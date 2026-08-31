"""One-shot shelf actions."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CollectShineConfigEntry, CollectShineCoordinator
from .entity import CollectShineEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CollectShineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DigButton(entry.runtime_data), ClearHighlightButton(entry.runtime_data)])


class DigButton(CollectShineEntity, ButtonEntity):
    """Let the shelf choose: a light runs along the strip and slows to a stop on a record."""

    _attr_translation_key = "dig"

    def __init__(self, coordinator: CollectShineCoordinator) -> None:
        super().__init__(coordinator, "dig")

    async def async_press(self) -> None:
        record = await self.coordinator.client.dig()

        if record is not None:
            _LOGGER.debug("CollectShine dug out %s", record.label)

        await self.coordinator.async_request_refresh()


class ClearHighlightButton(CollectShineEntity, ButtonEntity):
    """Put the shelf back to normal lighting after a record has been found."""

    _attr_translation_key = "clear_highlight"

    def __init__(self, coordinator: CollectShineCoordinator) -> None:
        super().__init__(coordinator, "clear_highlight")

    async def async_press(self) -> None:
        record = self.coordinator.data.now_playing or self.coordinator.data.last_played

        # Clearing is per-record on the base station, so with nothing to clear there is nothing
        # to do — rather than an error nobody can act on.
        if record is None:
            _LOGGER.debug("Nothing to clear on the CollectShine shelf")
            return

        await self.coordinator.client.clear_highlight(record.id)
        await self.coordinator.async_request_refresh()
