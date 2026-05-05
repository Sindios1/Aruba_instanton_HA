"""The Aruba Instant On integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aruba_api import ArubaInstantOnAPI
from .const import DOMAIN, CONF_SITE_ID, DEFAULT_POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aruba Instant On from a config entry."""
    session = async_get_clientsession(hass)
    api = ArubaInstantOnAPI(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session
    )

    if not await api.login():
        _LOGGER.error("Failed to login to Aruba Instant On")
        return False

    async def async_update_data():
        """Fetch data from API."""
        try:
            site_id = entry.data[CONF_SITE_ID]
            details = await api.get_site_details(site_id)
            inventory = await api.get_inventory(site_id)
            clients = await api.get_clients(site_id)
            
            return {
                "details": details,
                "inventory": inventory,
                "clients": clients,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_POLLING_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
