from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import ShenzhenWaterApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ShenzhenWaterCoordinator(DataUpdateCoordinator):
    """Shenzhen Water data coordinator."""

    def __init__(self, hass: HomeAssistant, api: ShenzhenWaterApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=6),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch latest data."""
        current = await self.api.async_get_bill_info()
    
        current_bill = {}
        rows = current.get("data") or []
        if rows:
            current_bill = rows[0]
    
        previous = None
        previous_month = current_bill.get("prebillmonth")
    
        if previous_month:
            try:
                previous = await self.api.async_get_bill_info(previous_month)
            except Exception as err:
                _LOGGER.warning("Failed to fetch previous bill: %s", err)
    
        return {
            "current": current,
            "previous": previous,
        }

    @property
    def bill(self) -> dict:
        """Return current bill item."""
        data = self.data or {}
        current = data.get("current") or {}
        rows = current.get("data") or []
        if not rows:
            return {}
        return rows[0]
    
    
    @property
    def meter(self) -> dict:
        """Return current meter item."""
        bill = self.bill
        meters = bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]

    @property
    def previous_bill(self) -> dict:
        """Return previous bill item."""
        data = self.data or {}
        previous = data.get("previous") or {}
        rows = previous.get("data") or []
        if not rows:
            return {}
        return rows[0]
    
    
    @property
    def previous_meter(self) -> dict:
        """Return previous meter item."""
        bill = self.previous_bill
        meters = bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]