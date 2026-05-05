"""Support for Aruba Instant On binary sensors."""
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SITE_NAME

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for Aruba Instant On."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    site_name = entry.data[CONF_SITE_NAME]

    async_add_entities([ArubaAlertBinarySensor(coordinator, entry, site_name)])

class ArubaAlertBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an Alert binary sensor."""

    def __init__(self, coordinator, entry, site_name):
        super().__init__(coordinator)
        self._attr_name = f"{site_name} Alerts"
        self._attr_unique_id = f"{entry.unique_id}_alerts"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        """Return true if there is a problem (alerts present)."""
        health = self.coordinator.data["details"].get("health")
        return health != "ok"

    @property
    def extra_state_attributes(self):
        """Return alert details."""
        return {
            "reason": self.coordinator.data["details"].get("healthReason"),
            "health": self.coordinator.data["details"].get("health")
        }
