"""Config flow for Aruba Instant On integration."""
import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_SITE_ID, CONF_SITE_NAME
from .aruba_api import ArubaInstantOnAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aruba Instant On."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = ArubaInstantOnAPI(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                session
            )

            try:
                if await api.login():
                    sites = await api.get_sites()
                    if not sites:
                        errors["base"] = "no_sites"
                    else:
                        self.user_input = user_input
                        self.sites = {site["id"]: site["name"] for site in sites}
                        return await self.async_step_site()
                else:
                    errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_site(self, user_input=None):
        """Handle the site selection step."""
        errors = {}
        if user_input is not None:
            site_id = user_input[CONF_SITE_ID]
            site_name = self.sites[site_id]
            
            await self.async_set_unique_id(site_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Aruba Site: {site_name}",
                data={
                    **self.user_input,
                    CONF_SITE_ID: site_id,
                    CONF_SITE_NAME: site_name,
                },
            )

        return self.async_show_form(
            step_id="site",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_ID): vol.In(self.sites),
                }
            ),
            errors=errors,
        )
