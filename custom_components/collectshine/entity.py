"""Shared entity base for CollectShine."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CollectShineCoordinator


class CollectShineEntity(CoordinatorEntity[CollectShineCoordinator]):
    """An entity belonging to one base station."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CollectShineCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        state = self.coordinator.data

        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.config_entry.unique_id))},
            name=state.device_name,
            manufacturer="CollectShine",
            model="Base Station",
            sw_version=state.firmware,
            configuration_url=f"http://{self.coordinator.client.host}/",
        )
