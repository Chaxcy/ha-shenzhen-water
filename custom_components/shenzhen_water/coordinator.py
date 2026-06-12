from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ShenzhenWaterApi,
    ShenzhenWaterApiError,
    ShenzhenWaterAuthExpiredError,
)
from .const import DEFAULT_UPDATE_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ShenzhenWaterCoordinator(DataUpdateCoordinator):
    """Shenzhen Water data coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ShenzhenWaterApi,
        update_interval_minutes: int = DEFAULT_UPDATE_INTERVAL_MINUTES,
    ) -> None:
        """Initialize Shenzhen Water coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch latest data."""
        try:
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
                except ShenzhenWaterAuthExpiredError:
                    raise
                except Exception as err:
                    _LOGGER.warning("Failed to fetch previous bill: %s", err)

            return {
                "current": current,
                "previous": previous,
            }

        except ShenzhenWaterAuthExpiredError as err:
            _LOGGER.error(
                "Shenzhen Water login expired. Please delete and re-add the "
                "integration to login again with SMS verification. Detail: %s",
                err,
            )
            raise UpdateFailed(
                "深圳水务登录已失效，请删除该集成配置项后重新添加，重新获取短信验证码登录。"
            ) from err

        except ShenzhenWaterApiError as err:
            _LOGGER.error("Shenzhen Water API error: %s", err)
            raise UpdateFailed(f"深圳水务接口错误：{err}") from err

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