from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi, ShenzhenWaterApiError
from .const import (
    CONF_CUSTOMER_CODE,
    CONF_OPENID,
    CONF_UTOKEN,
    DOMAIN,
)


class ShenzhenWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shenzhen Water."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            customer_code = str(user_input[CONF_CUSTOMER_CODE]).strip()
            openid = str(user_input[CONF_OPENID]).strip()
            utoken = str(user_input[CONF_UTOKEN]).strip()

            session = async_get_clientsession(self.hass)
            api = ShenzhenWaterApi(
                session,
                customer_code=customer_code,
                openid=openid,
                utoken=utoken,
            )

            try:
                await api.async_get_latest_bill_details()
            except ShenzhenWaterApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(customer_code)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"深圳水务 {customer_code}",
                    data={
                        CONF_CUSTOMER_CODE: customer_code,
                        CONF_OPENID: openid,
                        CONF_UTOKEN: utoken,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CUSTOMER_CODE): str,
                vol.Required(CONF_OPENID): str,
                vol.Required(CONF_UTOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
