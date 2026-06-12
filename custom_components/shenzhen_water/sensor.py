from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CUSTOMER_CODE
from .coordinator import ShenzhenWaterCoordinator


@dataclass(frozen=True, kw_only=True)
class ShenzhenWaterSensorDescription(SensorEntityDescription):
    """Shenzhen Water sensor description."""

    value_fn: Callable[[ShenzhenWaterCoordinator], Any]


SENSORS: tuple[ShenzhenWaterSensorDescription, ...] = (
    ShenzhenWaterSensorDescription(
        key="water_meter_reading",
        translation_key="water_meter_reading",
        name="当前水表读数",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda c: c.meter.get("waterNumber"),
    ),
    ShenzhenWaterSensorDescription(
        key="current_period_usage",
        translation_key="current_period_usage",
        name="本期用水量",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.bill.get("waterConsumption"),
    ),
    ShenzhenWaterSensorDescription(
        key="total_amount",
        translation_key="total_amount",
        name="本期总费用",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.bill.get("totalAmount"),
    ),
    ShenzhenWaterSensorDescription(
        key="needpay",
        translation_key="needpay",
        name="应缴金额",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.bill.get("needpay"),
    ),
    ShenzhenWaterSensorDescription(
        key="water_amount",
        translation_key="water_amount",
        name="自来水费",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.bill.get("waterAmount"),
    ),
    ShenzhenWaterSensorDescription(
        key="sewage_amount",
        translation_key="sewage_amount",
        name="污水处理费",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.bill.get("sewageAmount"),
    ),
    ShenzhenWaterSensorDescription(
        key="garbage_amount",
        translation_key="garbage_amount",
        name="垃圾费",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.bill.get("garbageAmount"),
    ),
    ShenzhenWaterSensorDescription(
        key="bill_month",
        translation_key="bill_month",
        name="账单月份",
        value_fn=lambda c: c.bill.get("costDate"),
    ),
    ShenzhenWaterSensorDescription(
        key="due_date",
        translation_key="due_date",
        name="到期日",
        value_fn=lambda c: c.bill.get("dueDate"),
    ),
    ShenzhenWaterSensorDescription(
        key="payment_status",
        translation_key="payment_status",
        name="缴费状态",
        value_fn=lambda c: c.bill.get("paymentStatus"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Shenzhen Water sensors."""
    coordinator: ShenzhenWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    customer_code = entry.data[CONF_CUSTOMER_CODE]

    async_add_entities(
        ShenzhenWaterSensor(coordinator, entry, customer_code, description)
        for description in SENSORS
    )


class ShenzhenWaterSensor(CoordinatorEntity[ShenzhenWaterCoordinator], SensorEntity):
    """Shenzhen Water sensor."""

    entity_description: ShenzhenWaterSensorDescription

    def __init__(
        self,
        coordinator: ShenzhenWaterCoordinator,
        entry: ConfigEntry,
        customer_code: str,
        description: ShenzhenWaterSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, customer_code)},
            "name": f"深圳水务 {customer_code}",
            "manufacturer": "Shenzhen Water",
        }

    @property
    def native_value(self):
        """Return native value."""
        return self.entity_description.value_fn(self.coordinator)