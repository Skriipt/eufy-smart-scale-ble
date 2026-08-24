"""Sensor entities for Eufy Smart Scale P3 BLE."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Final, override

from homeassistant.components.bluetooth import async_address_present
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL_NAME
from .models import EufyP3RuntimeData, ScaleState

ValueType = float | int | str | datetime | None
ValueGetter = Callable[[ScaleState], ValueType]

STATUS_OPTIONS: Final = [
    "live",
    "locked",
    "post_lock",
    "impedance",
    "body_composition",
    "body_composition_late",
    "complete",
]

WEIGHT_DESCRIPTION = SensorEntityDescription(
    key="weight",
    translation_key="weight",
    device_class=SensorDeviceClass.WEIGHT,
    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=2,
)
REAL_TIME_WEIGHT_DESCRIPTION = SensorEntityDescription(
    key="real_time_weight",
    translation_key="real_time_weight",
    device_class=SensorDeviceClass.WEIGHT,
    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=2,
)
IMPEDANCE_DESCRIPTION = SensorEntityDescription(
    key="impedance",
    translation_key="impedance",
    native_unit_of_measurement="Ω",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:omega",
    suggested_display_precision=1,
)
HEART_RATE_DESCRIPTION = SensorEntityDescription(
    key="heart_rate",
    translation_key="heart_rate",
    native_unit_of_measurement="bpm",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:heart-pulse",
)
LAST_MEASUREMENT_DESCRIPTION = SensorEntityDescription(
    key="last_measurement",
    translation_key="last_measurement",
    device_class=SensorDeviceClass.TIMESTAMP,
    icon="mdi:clock-check-outline",
)
PACKET_STATUS_DESCRIPTION = SensorEntityDescription(
    key="packet_status",
    translation_key="packet_status",
    device_class=SensorDeviceClass.ENUM,
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:bluetooth-transfer",
)

RESTORED_DESCRIPTIONS: Final[
    tuple[tuple[SensorEntityDescription, ValueGetter], ...]
] = (
    (WEIGHT_DESCRIPTION, lambda state: state.weight_kg),
    (IMPEDANCE_DESCRIPTION, lambda state: state.impedance_ohm),
    (HEART_RATE_DESCRIPTION, lambda state: state.heart_rate_bpm),
    (LAST_MEASUREMENT_DESCRIPTION, lambda state: state.last_measurement_at),
)


def _normalized_address(address: str) -> str:
    return "".join(character for character in address.lower() if character.isalnum())


def _device_info(address: str) -> DeviceInfo:
    return DeviceInfo(
        name=DEVICE_NAME,
        manufacturer=MANUFACTURER,
        model=MODEL_NAME,
        identifiers={(DOMAIN, address)},
        connections={(dr.CONNECTION_BLUETOOTH, address)},
    )


class _EufyP3EntityMixin:
    """Shared callback and device metadata for all scale entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        data: EufyP3RuntimeData,
        description: SensorEntityDescription,
    ) -> None:
        self.entity_description = description
        self._data = data
        self._attr_unique_id = f"{_normalized_address(data.address)}_{description.key}"
        self._attr_device_info = _device_info(data.address)
        if description.device_class is SensorDeviceClass.ENUM:
            self._attr_options = STATUS_OPTIONS

    @callback
    def _handle_device_update(self, state: ScaleState) -> None:
        self._apply_state(state)
        self.async_write_ha_state()

    def _apply_state(self, state: ScaleState) -> None:
        """Apply a state update in subclasses."""
        raise NotImplementedError

    def _subscribe_for_test(self) -> None:
        """Subscribe without adding to HA; intentionally private test seam."""
        self._data.device.register_callback(self._handle_device_update)

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._data.device.register_callback(self._handle_device_update)
        )


class EufyP3RestoredSensor(_EufyP3EntityMixin, RestoreSensor):
    """A completed measurement that survives Home Assistant restarts."""

    def __init__(
        self,
        data: EufyP3RuntimeData,
        description: SensorEntityDescription,
        value_getter: ValueGetter,
    ) -> None:
        super().__init__(data, description)
        self._value_getter = value_getter
        self._attr_native_value: ValueType = None

    @property
    @override
    def available(self) -> bool:
        return True

    @property
    @override
    def native_value(self) -> ValueType:
        return self._attr_native_value

    @override
    def _apply_state(self, state: ScaleState) -> None:
        value = self._value_getter(state)
        if value is not None:
            self._attr_native_value = value

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if last_sensor_data := await self.async_get_last_sensor_data():
            self._attr_native_value = last_sensor_data.native_value
        self._apply_state(self._data.device.state)


class EufyP3RealTimeWeightSensor(_EufyP3EntityMixin, SensorEntity):
    """Live weight while the user is standing on the scale."""

    def __init__(self, data: EufyP3RuntimeData) -> None:
        super().__init__(data, REAL_TIME_WEIGHT_DESCRIPTION)

    @property
    @override
    def available(self) -> bool:
        return async_address_present(self.hass, self._data.address)

    @property
    @override
    def native_value(self) -> float | None:
        return self._data.device.state.real_time_weight_kg

    @override
    def _apply_state(self, state: ScaleState) -> None:
        return None


class EufyP3PacketStatusSensor(_EufyP3EntityMixin, SensorEntity):
    """Diagnostic view of the last accepted P3 packet phase."""

    def __init__(self, data: EufyP3RuntimeData) -> None:
        super().__init__(data, PACKET_STATUS_DESCRIPTION)

    @property
    @override
    def available(self) -> bool:
        return async_address_present(self.hass, self._data.address)

    @property
    @override
    def native_value(self) -> str | None:
        status = self._data.device.state.packet_status
        return status.slug if status is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._data.device.state
        return {
            "status_hex": (
                f"0x{state.packet_status.value:02X}"
                if state.packet_status is not None
                else None
            ),
            "sequence": state.sequence,
            "raw_packet": state.raw_packet_hex,
        }

    @override
    def _apply_state(self, state: ScaleState) -> None:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create all Eufy P3 sensors."""
    data: EufyP3RuntimeData = entry.runtime_data
    entities: list[SensorEntity] = [
        EufyP3RestoredSensor(data, description, getter)
        for description, getter in RESTORED_DESCRIPTIONS
    ]
    entities.extend(
        [
            EufyP3RealTimeWeightSensor(data),
            EufyP3PacketStatusSensor(data),
        ]
    )
    async_add_entities(entities)
