from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_OPENID,
    CONF_GUID,
    CONF_CUSTOMER_CODE,
    CONF_BILL_MONTH,
    CONF_TENANT_ID,
    CONF_UTOKEN,
    CONF_REQUEST_HEADER_VALUE,
)


# 临时默认值，方便本地测试。

DEFAULT_OPENID = ""
DEFAULT_GUID = ""
DEFAULT_CUSTOMER_CODE = ""
DEFAULT_BILL_MONTH = 
DEFAULT_TENANT_ID = "18a85453-ee3f-xxx-xxx-xxx"
DEFAULT_UTOKEN = "cde1d4eb-91d3-xxx-xxx-xxx"
DEFAULT_REQUEST_HEADER_VALUE = ""


class ShenzhenWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Shenzhen Water."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CUSTOMER_CODE])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"深圳水务 {user_input[CONF_CUSTOMER_CODE]}",
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CUSTOMER_CODE, default=DEFAULT_CUSTOMER_CODE): str,
                vol.Required(CONF_BILL_MONTH, default=DEFAULT_BILL_MONTH): int,
                vol.Required(CONF_OPENID, default=DEFAULT_OPENID): str,
                vol.Required(CONF_GUID, default=DEFAULT_GUID): str,
                vol.Required(CONF_TENANT_ID, default=DEFAULT_TENANT_ID): str,
                vol.Required(CONF_UTOKEN, default=DEFAULT_UTOKEN): str,
                vol.Required(
                    CONF_REQUEST_HEADER_VALUE,
                    default=DEFAULT_REQUEST_HEADER_VALUE,
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )