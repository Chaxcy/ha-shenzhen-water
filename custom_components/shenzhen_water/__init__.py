from __future__ import annotations

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi
from .const import (
    CONF_APP_USER_ID,
    CONF_BILL_MONTH,
    CONF_CTOKEN,
    CONF_CUSTOMER_CODE,
    CONF_GUID,
    CONF_OPENID,
    CONF_TENANT_ID,
    CONF_UPDATE_INTERVAL_MINUTES,
    CONF_UTOKEN,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
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
        ctoken=entry.data.get(CONF_CTOKEN, ""),
    )

    update_interval_minutes = int(
        entry.options.get(
            CONF_UPDATE_INTERVAL_MINUTES,
            entry.data.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
            ),
        )
    )

    coordinator = ShenzhenWaterCoordinator(
        hass,
        api,
        update_interval_minutes=update_interval_minutes,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Shenzhen Water config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Shenzhen Water config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)