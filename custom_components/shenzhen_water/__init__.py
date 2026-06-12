from __future__ import annotations

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi
from .const import (
    DOMAIN,
    CONF_OPENID,
    CONF_GUID,
    CONF_CUSTOMER_CODE,
    CONF_BILL_MONTH,
    CONF_TENANT_ID,
    CONF_UTOKEN,
    CONF_APP_USER_ID,
)
from .coordinator import ShenzhenWaterCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shenzhen Water from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session: ClientSession = async_get_clientsession(hass)

    api = ShenzhenWaterApi(
        session=session,
        tenant_id=entry.data[CONF_TENANT_ID],
        openid=entry.data[CONF_OPENID],
        guid=entry.data[CONF_GUID],
        customer_code=entry.data[CONF_CUSTOMER_CODE],
        bill_month=entry.data[CONF_BILL_MONTH],
        utoken=entry.data[CONF_UTOKEN],
        app_user_id=entry.data.get(CONF_APP_USER_ID, ""),
    )

    coordinator = ShenzhenWaterCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Shenzhen Water config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok