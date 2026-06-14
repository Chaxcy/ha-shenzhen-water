from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi, ShenzhenWaterApiError
from .const import (
    CONF_CUSTOMER_CODE,
    CONF_OPENID,
    DOMAIN,
)


class ShenzhenWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shenzhen Water."""

    VERSION = 1
    _openid: str
    _accounts: list[dict[str, Any]]

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            openid = str(user_input[CONF_OPENID]).strip()

            session = async_get_clientsession(self.hass)
            api = ShenzhenWaterApi(
                session,
                customer_code="",
                openid=openid,
            )

            try:
                users = await api.async_get_users()
            except ShenzhenWaterApiError:
                errors["base"] = "cannot_connect"
            else:
                accounts = [
                    account
                    for account in users.get("data") or []
                    if account.get("customerCode")
                ]
                if not accounts:
                    errors["base"] = "no_accounts"
                elif len(accounts) == 1:
                    return await self._async_create_account_entry(
                        openid,
                        str(accounts[0].get("customerCode") or "").strip(),
                    )
                else:
                    self._openid = openid
                    self._accounts = accounts
                    return await self.async_step_account()

        schema = vol.Schema(
            {
                vol.Required(CONF_OPENID): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_account(self, user_input=None):
        """Let the user choose one account when OpenId has multiple bindings."""
        errors = {}

        account_options = {
            str(account.get("customerCode")): self._format_account(account)
            for account in self._accounts
            if account.get("customerCode")
        }

        if user_input is not None:
            customer_code = str(user_input[CONF_CUSTOMER_CODE]).strip()
            if customer_code not in account_options:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create_account_entry(
                    self._openid,
                    customer_code,
                )

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CUSTOMER_CODE): vol.In(account_options),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def _format_account(account: dict[str, Any]) -> str:
        customer_code = str(account.get("customerCode") or "")
        name = str(account.get("customerName") or "")
        address = str(account.get("address") or "")
        label_parts = [part for part in (customer_code, name, address) if part]
        return " - ".join(label_parts) or customer_code

    async def _async_create_account_entry(self, openid: str, customer_code: str):
        if not customer_code:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(customer_code)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"深圳水务 {customer_code}",
            data={
                CONF_CUSTOMER_CODE: customer_code,
                CONF_OPENID: openid,
            },
        )
