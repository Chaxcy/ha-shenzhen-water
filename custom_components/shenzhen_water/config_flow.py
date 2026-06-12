from __future__ import annotations

import logging

import voluptuous as vol
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi, ShenzhenWaterApiError
from .const import (
    DEFAULT_TENANT_ID,
    CONF_APP_USER_ID,
    CONF_BILL_MONTH,
    CONF_CUSTOMER_CODE,
    CONF_GUID,
    CONF_MOBILE,
    CONF_OPENID,
    CONF_TENANT_ID,
    CONF_UTOKEN,
    CONF_CTOKEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class ShenzhenWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Shenzhen Water."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._mobile: str | None = None
        self._tenant_id: str = DEFAULT_TENANT_ID

    async def async_step_user(self, user_input=None):
        """Step 1: input mobile number and send SMS code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._mobile = str(user_input[CONF_MOBILE]).strip()
            self._tenant_id = DEFAULT_TENANT_ID

            try:
                session = async_get_clientsession(self.hass)

                api = ShenzhenWaterApi(
                    session=session,
                    tenant_id=self._tenant_id,
                )

                await api.async_send_sms_code(self._mobile)

                return await self.async_step_sms()

            except ShenzhenWaterApiError as err:
                _LOGGER.exception("Failed to send Shenzhen Water SMS code: %s", err)
                errors["base"] = "send_sms_failed"

            except (ClientError, TimeoutError) as err:
                _LOGGER.exception("Network error while sending SMS code: %s", err)
                errors["base"] = "cannot_connect"

            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error while sending SMS code: %s", err)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_MOBILE): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_sms(self, user_input=None):
        """Step 2: input SMS code, login, fetch customer code and latest bill month."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sms_code = str(user_input["sms_code"]).strip()

            if not self._mobile:
                errors["base"] = "missing_mobile"
            else:
                try:
                    session = async_get_clientsession(self.hass)

                    login_api = ShenzhenWaterApi(
                        session=session,
                        tenant_id=self._tenant_id,
                    )

                    login_result = await login_api.async_login_v20(
                        mobile=self._mobile,
                        sms_code=sms_code,
                    )

                    login_data = login_result.get("data") or {}

                    openid = str(login_data.get("mobile") or self._mobile)
                    guid = str(login_data.get("guid") or "")
                    utoken = str(login_data.get("token") or "")
                    app_user_id = str(login_data.get("appUserId") or "")

                    if not openid or not guid or not utoken:
                        _LOGGER.error(
                            "Invalid LoginV20 data: %s",
                            login_data,
                        )
                        errors["base"] = "login_failed"
                    else:
                        api = ShenzhenWaterApi(
                            session=session,
                            tenant_id=self._tenant_id,
                            openid=openid,
                            guid=guid,
                            utoken=utoken,
                            app_user_id=app_user_id,
                        )

                        users_result = await api.async_get_users_v20()
                        users = users_result.get("data") or []

                        if not users:
                            _LOGGER.error(
                                "No Shenzhen Water customer found: %s",
                                users_result,
                            )
                            errors["base"] = "no_customer"
                        else:
                            # 第一版先默认取第一个绑定户号。
                            customer = users[0]
                            customer_code = str(customer.get("customerCode") or "")
                            
                            if not customer_code:
                                _LOGGER.error(
                                    "customerCode not found in user data: %s",
                                    customer,
                                )
                                errors["base"] = "no_customer"
                            
                            else:
                                ctoken = await api.async_generate_ctoken(customer_code)
                            
                                latest_result = await api.async_get_latest_bill_details(customer_code)
                                latest_rows = latest_result.get("data") or []
                            
                                if not latest_rows:
                                    _LOGGER.error(
                                        "No latest bill found: %s",
                                        latest_result,
                                    )
                                    errors["base"] = "no_latest_bill"
                                else:
                                    latest_bill = latest_rows[0]
                                    bill_month = latest_bill.get("costDate")
                            
                                    if not bill_month:
                                        _LOGGER.error(
                                            "costDate not found in latest bill: %s",
                                            latest_bill,
                                        )
                                        errors["base"] = "no_latest_bill"
                                    else:
                                        bill_month = int(bill_month)
                            
                                        await self.async_set_unique_id(customer_code)
                                        self._abort_if_unique_id_configured()
                            
                                        title_name = customer.get("customerName") or customer_code
                            
                                        return self.async_create_entry(
                                            title=f"深圳水务 {title_name}",
                                            data={
                                                CONF_MOBILE: self._mobile,
                                                CONF_OPENID: openid,
                                                CONF_GUID: guid,
                                                CONF_UTOKEN: utoken,
                                                CONF_APP_USER_ID: app_user_id,
                                                CONF_TENANT_ID: self._tenant_id,
                                                CONF_CUSTOMER_CODE: customer_code,
                                                CONF_BILL_MONTH: bill_month,
                                                CONF_CTOKEN: ctoken,
                                            },
                                        )
                            
                                            except ShenzhenWaterApiError as err:
                                                _LOGGER.exception("Shenzhen Water login/config failed: %s", err)
                                                errors["base"] = "api_error"
                            
                                            except (ClientError, TimeoutError) as err:
                                                _LOGGER.exception("Network error during Shenzhen Water login: %s", err)
                                                errors["base"] = "cannot_connect"
                            
                                            except Exception as err:  # noqa: BLE001
                                                _LOGGER.exception("Unexpected error during Shenzhen Water login: %s", err)
                                                errors["base"] = "unknown"
                            
                                    data_schema = vol.Schema(
                                        {
                                            vol.Required("sms_code"): str,
                                        }
                                    )
                            
                                    return self.async_show_form(
                                        step_id="sms",
                                        data_schema=data_schema,
                                        errors=errors,
                                        description_placeholders={
                                            "mobile": self._mobile or "",
                                        },
                                    )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return options flow."""
        return ShenzhenWaterOptionsFlow(config_entry)


class ShenzhenWaterOptionsFlow(config_entries.OptionsFlow):
    """Options flow placeholder for Shenzhen Water."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            errors={},
        )
