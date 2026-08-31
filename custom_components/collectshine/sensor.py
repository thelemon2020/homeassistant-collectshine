"""Sensors describing what the shelf is doing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import BaseStationState, Record
from .coordinator import CollectShineConfigEntry
from .entity import CollectShineEntity

# A state longer than this is refused by the state machine, and a long title plus a long artist
# gets closer than you would think.
MAX_STATE_LENGTH = 255


@dataclass(frozen=True, kw_only=True)
class CollectShineSensorDescription(SensorEntityDescription):
    """How one sensor reads itself out of a poll."""

    value: Callable[[BaseStationState], str | int | None]
    attributes: Callable[[BaseStationState], dict[str, Any]] | None = None


def _record_attributes(record: Record | None) -> dict[str, Any]:
    if record is None:
        return {}

    # The id is the part that matters: it is what every acting endpoint on the base station keys
    # on, so an automation that reacts to a sensor can also do something about it.
    return {"release_id": record.id, "artist": record.artist, "title": record.title}


SENSORS: tuple[CollectShineSensorDescription, ...] = (
    CollectShineSensorDescription(
        key="now_playing",
        translation_key="now_playing",
        value=lambda state: state.now_playing.label if state.now_playing else None,
        attributes=lambda state: _record_attributes(state.now_playing),
    ),
    CollectShineSensorDescription(
        key="last_played",
        translation_key="last_played",
        value=lambda state: state.last_played.label if state.last_played else None,
        attributes=lambda state: _record_attributes(state.last_played),
    ),
    CollectShineSensorDescription(
        key="collection_size",
        translation_key="collection_size",
        native_unit_of_measurement="records",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda state: state.release_count,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CollectShineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        CollectShineSensor(entry.runtime_data, description) for description in SENSORS
    )


class CollectShineSensor(CollectShineEntity, SensorEntity):
    entity_description: CollectShineSensorDescription

    def __init__(self, coordinator, description: CollectShineSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | None:
        value = self.entity_description.value(self.coordinator.data)

        if isinstance(value, str) and len(value) > MAX_STATE_LENGTH:
            return value[: MAX_STATE_LENGTH - 1] + "…"

        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.entity_description.attributes is None:
            return {}

        return self.entity_description.attributes(self.coordinator.data)
