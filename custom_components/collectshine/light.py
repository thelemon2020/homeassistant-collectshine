"""The shelf lights, as a switch."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CollectShineConfigEntry, CollectShineCoordinator
from .entity import CollectShineEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CollectShineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([ShelfLight(entry.runtime_data)])


class ShelfLight(CollectShineEntity, LightEntity):
    """Master power for every shelf this base station drives.

    On and off only, deliberately. The LED controllers run stock WLED and Home Assistant's own
    WLED integration already exposes colour, effects and palettes better than a passthrough could
    — and anyone who has lit their shelves probably has it installed. What this integration owns,
    and WLED cannot, is the whole-house power state and the record-level spotlight.

    Master power also matters more than it looks: a colour, palette or spotlight sent to a strip
    that is switched off is accepted and shows nothing at all, so this is the switch that decides
    whether anything else the shelf does is visible.
    """

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.ONOFF}
    _attr_translation_key = "shelf"

    def __init__(self, coordinator: CollectShineCoordinator) -> None:
        super().__init__(coordinator, "shelf_light")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.lights_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, on: bool) -> None:
        await self.coordinator.client.set_lights(on)

        # Show the change at once, then confirm it. The base station fans out to every WLED
        # controller and waits for them, so the poll behind this can take a moment.
        self.coordinator.data.lights_on = on
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
