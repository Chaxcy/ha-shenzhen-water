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
        return await self.api.async_get_bill_info()

    @property
    def bill(self) -> dict:
        """Return first bill item."""
        data = self.data or {}
        rows = data.get("data") or []
        if not rows:
            return {}
        return rows[0]

    @property
    def meter(self) -> dict:
        """Return first meter item."""
        bill = self.bill
        meters = bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]