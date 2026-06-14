from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ShenzhenWaterApi, ShenzhenWaterApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ShenzhenWaterCoordinator(DataUpdateCoordinator):
    """Shenzhen Water data coordinator."""

    def __init__(self, hass, api: ShenzhenWaterApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=360),
        )
        self.api = api

    async def _async_update_data(self):
        try:
            return await self.api.async_get_all()
        except ShenzhenWaterApiError as err:
            raise UpdateFailed(str(err)) from err

    @property
    def bill(self) -> dict:
        data = self.data or {}
        current = data.get("current") or {}
        rows = current.get("data") or []
        if not rows:
            return {}
        return rows[0]

    @property
    def meter(self) -> dict:
        meters = self.bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]

    @property
    def previous_bill(self) -> dict:
        data = self.data or {}
        previous = data.get("previous") or {}
        rows = previous.get("data") or []
        if not rows:
            return {}
        return rows[0]

    @property
    def previous_meter(self) -> dict:
        meters = self.previous_bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]
