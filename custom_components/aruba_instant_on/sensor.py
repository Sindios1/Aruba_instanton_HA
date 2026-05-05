"""Support for Aruba Instant On sensors."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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
    """Set up sensors for Aruba Instant On."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    site_name = entry.data[CONF_SITE_NAME]

    entities = []

    # Site Health Sensor
    entities.append(ArubaSiteHealthSensor(coordinator, entry, site_name))
    
    # Client Count Sensors
    entities.append(ArubaClientCountSensor(coordinator, entry, site_name, "Wired", "wiredClientsCount"))
    entities.append(ArubaClientCountSensor(coordinator, entry, site_name, "Wireless", "wirelessClientsCount"))

    # Device Sensors (from inventory)
    for device in coordinator.data["inventory"]:
        entities.append(ArubaDeviceStatusSensor(coordinator, entry, device))

    async_add_entities(entities)

class ArubaSiteHealthSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Site Health sensor."""

    def __init__(self, coordinator, entry, site_name):
        super().__init__(coordinator)
        self._site_name = site_name
        self._attr_name = f"{site_name} Health"
        self._attr_unique_id = f"{entry.unique_id}_health"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data["details"].get("health")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "reason": self.coordinator.data["details"].get("healthReason")
        }

class ArubaClientCountSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Client Count sensor."""

    def __init__(self, coordinator, entry, site_name, client_type, key):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"{site_name} {client_type} Clients"
        self._attr_unique_id = f"{entry.unique_id}_{client_type.lower()}_clients"
        self._attr_native_unit_of_measurement = "clients"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data["details"].get(self._key)

class ArubaDeviceStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Device Status sensor."""

    def __init__(self, coordinator, entry, device):
        super().__init__(coordinator)
        self._device_id = device["id"]
        self._attr_name = f"Aruba {device['name']} Status"
        self._attr_unique_id = f"device_{device['id']}_status"

    @property
    def state(self):
        """Return the state of the sensor."""
        # Find the device in the updated inventory
        for d in self.coordinator.data["inventory"]:
            if d["id"] == self._device_id:
                return d.get("status")
        return "unknown"

    @property
    def extra_state_attributes(self):
        """Return device attributes."""
        for d in self.coordinator.data["inventory"]:
            if d["id"] == self._device_id:
                return {
                    "ip_address": d.get("ipAddress"),
                    "mac_address": d.get("macAddress"),
                    "model": d.get("model"),
                    "serial_number": d.get("serialNumber"),
                    "uptime": d.get("uptimeInSeconds"),
                    "device_type": d.get("deviceType")
                }
        return {}
