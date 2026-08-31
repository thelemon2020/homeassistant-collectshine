"""Whether the record on the turntable is due to be turned over."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CollectShineConfigEntry, CollectShineCoordinator
from .entity import CollectShineEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CollectShineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([FlipDueBinarySensor(entry.runtime_data)])


class FlipDueBinarySensor(CollectShineEntity, BinarySensorEntity):
    """Side A has run out.

    Exposed because it is the one thing in the product that is genuinely time-critical and that a
    house can act on by itself — a lamp flash, a phone notification — without anybody having to be
    looking at an app.
    """

    _attr_translation_key = "flip_due"

    def __init__(self, coordinator: CollectShineCoordinator) -> None:
        super().__init__(coordinator, "flip_due")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.flip_due
