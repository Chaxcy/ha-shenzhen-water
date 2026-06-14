from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi
from .const import (
    CONF_CHANNEL,
    CONF_CUSTOMER_CODE,
    CONF_GUID,
    CONF_TENANT_ID,
    CONF_UTOKEN,
    DEFAULT_CHANNEL,
    DEFAULT_TENANT_ID,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ShenzhenWaterCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shenzhen Water from a config entry."""
    session = async_get_clientsession(hass)

    api = ShenzhenWaterApi(
        session,
        customer_code=entry.data[CONF_CUSTOMER_CODE],
        guid=entry.data[CONF_GUID],
        utoken=entry.data[CONF_UTOKEN],
        tenant_id=entry.data.get(CONF_TENANT_ID, DEFAULT_TENANT_ID),
        channel=entry.data.get(CONF_CHANNEL, DEFAULT_CHANNEL),
    )

    coordinator = ShenzhenWaterCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Shenzhen Water config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
