"""Sensor entities for Eufy Smart Scale BLE."""

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
from homeassistant.const import EntityCategory, UnitOfMass, UnitOfRatio
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .body_composition import (
    ALGORITHM_ID,
    ALGORITHM_STATUS,
    BodyCompositionResult,
    BodyType,
)
from .const import DOMAIN, MANUFACTURER
from .model_registry import Capability, capability_enabled
from .models import EufyScaleRuntimeData, ScaleState

ValueType = float | int | str | datetime | None
ValueGetter = Callable[[ScaleState], ValueType]
CalculatedValueGetter = Callable[[BodyCompositionResult], float | int | str]

BODY_TYPE_OPTIONS: Final = [value.value for value in BodyType]

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
BATTERY_DESCRIPTION = SensorEntityDescription(
    key="battery",
    translation_key="battery",
    device_class=SensorDeviceClass.BATTERY,
    native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
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
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:bluetooth-transfer",
)

CALCULATED_DESCRIPTIONS: Final[
    tuple[tuple[SensorEntityDescription, CalculatedValueGetter], ...]
] = (
    (
        SensorEntityDescription(
            key="bmi",
            translation_key="bmi",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:human-male-height-variant",
            suggested_display_precision=1,
        ),
        lambda result: result.bmi,
    ),
    (
        SensorEntityDescription(
            key="body_fat",
            translation_key="body_fat",
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:percent",
            suggested_display_precision=1,
        ),
        lambda result: result.body_fat_percent,
    ),
    (
        SensorEntityDescription(
            key="body_fat_mass",
            translation_key="body_fat_mass",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:weight-kilogram",
            suggested_display_precision=1,
        ),
        lambda result: result.body_fat_mass_kg,
    ),
    (
        SensorEntityDescription(
            key="lean_body_mass",
            translation_key="lean_body_mass",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:weight-kilogram",
            suggested_display_precision=1,
        ),
        lambda result: result.lean_body_mass_kg,
    ),
    (
        SensorEntityDescription(
            key="muscle_mass",
            translation_key="muscle_mass",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:arm-flex",
            suggested_display_precision=1,
        ),
        lambda result: result.muscle_mass_kg,
    ),
    (
        SensorEntityDescription(
            key="bone_mass",
            translation_key="bone_mass",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:bone",
            suggested_display_precision=1,
        ),
        lambda result: result.bone_mass_kg,
    ),
    (
        SensorEntityDescription(
            key="body_water",
            translation_key="body_water",
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:water-percent",
            suggested_display_precision=1,
        ),
        lambda result: result.body_water_percent,
    ),
    (
        SensorEntityDescription(
            key="bmr",
            translation_key="bmr",
            native_unit_of_measurement="kcal/day",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:fire",
        ),
        lambda result: result.bmr_kcal_per_day,
    ),
    (
        SensorEntityDescription(
            key="visceral_fat",
            translation_key="visceral_fat",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:counter",
        ),
        lambda result: result.visceral_fat_level,
    ),
    (
        SensorEntityDescription(
            key="protein",
            translation_key="protein",
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:food-steak",
            suggested_display_precision=1,
        ),
        lambda result: result.protein_percent,
    ),
    (
        SensorEntityDescription(
            key="skeletal_muscle_mass",
            translation_key="skeletal_muscle_mass",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:arm-flex-outline",
            suggested_display_precision=1,
        ),
        lambda result: result.skeletal_muscle_mass_kg,
    ),
    (
        SensorEntityDescription(
            key="subcutaneous_fat",
            translation_key="subcutaneous_fat",
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:percent-outline",
            suggested_display_precision=1,
        ),
        lambda result: result.subcutaneous_fat_percent,
    ),
    (
        SensorEntityDescription(
            key="body_age",
            translation_key="body_age",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:calendar-account",
        ),
        lambda result: result.body_age_years,
    ),
    (
        SensorEntityDescription(
            key="body_type",
            translation_key="body_type",
            device_class=SensorDeviceClass.ENUM,
            icon="mdi:human",
        ),
        lambda result: result.body_type.value,
    ),
)


def _normalized_address(address: str) -> str:
    return "".join(character for character in address.lower() if character.isalnum())


def _device_info(data: EufyScaleRuntimeData) -> DeviceInfo:
    return DeviceInfo(
        name=data.model.display_name,
        manufacturer=MANUFACTURER,
        model=data.model.model_name,
        identifiers={(DOMAIN, data.address)},
        connections={(dr.CONNECTION_BLUETOOTH, data.address)},
    )


class _EufyScaleEntityMixin:
    """Shared callback and device metadata for raw scale entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        data: EufyScaleRuntimeData,
        description: SensorEntityDescription,
    ) -> None:
        self.entity_description = description
        self._data = data
        self._attr_unique_id = f"{_normalized_address(data.address)}_{description.key}"
        self._attr_device_info = _device_info(data)

    @callback
    def _handle_device_update(self, state: ScaleState) -> None:
        self._apply_state(state)
        self.async_write_ha_state()

    def _apply_state(self, state: ScaleState) -> None:
        """Apply a state update in subclasses."""
        raise NotImplementedError

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._data.device.register_callback(self._handle_device_update)
        )


class EufyScaleRestoredSensor(_EufyScaleEntityMixin, RestoreSensor):
    """A completed raw measurement that survives Home Assistant restarts."""

    def __init__(
        self,
        data: EufyScaleRuntimeData,
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


class EufyScaleRealTimeWeightSensor(_EufyScaleEntityMixin, SensorEntity):
    """Live weight while the user is standing on the scale."""

    def __init__(self, data: EufyScaleRuntimeData) -> None:
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


class EufyScaleBatterySensor(_EufyScaleEntityMixin, SensorEntity):
    """Battery percentage reported over GATT."""

    def __init__(self, data: EufyScaleRuntimeData) -> None:
        super().__init__(data, BATTERY_DESCRIPTION)

    @property
    @override
    def native_value(self) -> int | None:
        return self._data.device.state.battery_percent

    @override
    def _apply_state(self, state: ScaleState) -> None:
        return None


class EufyScalePacketStatusSensor(_EufyScaleEntityMixin, SensorEntity):
    """Diagnostic view of the last accepted protocol/session state."""

    def __init__(self, data: EufyScaleRuntimeData) -> None:
        super().__init__(data, PACKET_STATUS_DESCRIPTION)

    @property
    @override
    def available(self) -> bool:
        return async_address_present(self.hass, self._data.address)

    @property
    @override
    def native_value(self) -> str | None:
        status = self._data.device.state.packet_status
        return status

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._data.device.state
        return {"sequence": state.sequence}

    @override
    def _apply_state(self, state: ScaleState) -> None:
        return None


class EufyScaleCalculatedSensor(SensorEntity):
    """One locally calculated body-composition estimate."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        data: EufyScaleRuntimeData,
        description: SensorEntityDescription,
        value_getter: CalculatedValueGetter,
    ) -> None:
        self.entity_description = description
        self._data = data
        self._value_getter = value_getter
        self._attr_unique_id = f"{_normalized_address(data.address)}_{description.key}"
        self._attr_device_info = _device_info(data)
        if description.device_class is SensorDeviceClass.ENUM:
            self._attr_options = BODY_TYPE_OPTIONS

    @property
    @override
    def available(self) -> bool:
        return self._data.composition.result is not None

    @property
    @override
    def native_value(self) -> float | int | str | None:
        result = self._data.composition.result
        return self._value_getter(result) if result is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        manager = self._data.composition
        profile = manager.profile
        measurement = manager.measurement
        return {
            "source": "locally_calculated",
            "algorithm": ALGORITHM_ID,
            "algorithm_status": ALGORITHM_STATUS,
            "algorithm_basis_model": "T9150",
            "model_support": self._data.model.capability(
                Capability.BODY_COMPOSITION
            ).level.value,
            "input_weight_kg": (
                measurement.weight_kg if measurement is not None else None
            ),
            "input_impedance_ohm": (
                measurement.impedance_ohm if measurement is not None else None
            ),
            "measurement_timestamp": (
                measurement.measured_at.isoformat() if measurement is not None else None
            ),
            "profile_sex": profile.sex.value if profile is not None else None,
            "profile_height_cm": profile.height_cm if profile is not None else None,
            "profile_age": profile.age if profile is not None else None,
            "profile_mode": profile.mode.value if profile is not None else None,
        }

    @callback
    def _handle_composition_update(self, _result: BodyCompositionResult | None) -> None:
        self.async_write_ha_state()

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._data.composition.register_callback(self._handle_composition_update)
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create only entities supported by the configured scale model."""
    data: EufyScaleRuntimeData = entry.runtime_data
    options = entry.options
    entities: list[SensorEntity] = []

    if capability_enabled(data.model, Capability.FINAL_WEIGHT, options):
        entities.append(
            EufyScaleRestoredSensor(
                data, WEIGHT_DESCRIPTION, lambda state: state.weight_kg
            )
        )
        entities.append(
            EufyScaleRestoredSensor(
                data,
                LAST_MEASUREMENT_DESCRIPTION,
                lambda state: state.last_measurement_at,
            )
        )
    if capability_enabled(data.model, Capability.LIVE_WEIGHT, options):
        entities.append(EufyScaleRealTimeWeightSensor(data))
    if capability_enabled(data.model, Capability.IMPEDANCE, options):
        entities.append(
            EufyScaleRestoredSensor(
                data, IMPEDANCE_DESCRIPTION, lambda state: state.impedance_ohm
            )
        )
    if capability_enabled(data.model, Capability.HEART_RATE, options):
        entities.append(
            EufyScaleRestoredSensor(
                data, HEART_RATE_DESCRIPTION, lambda state: state.heart_rate_bpm
            )
        )
    if capability_enabled(data.model, Capability.BATTERY, options):
        entities.append(EufyScaleBatterySensor(data))

    entities.append(EufyScalePacketStatusSensor(data))

    if capability_enabled(data.model, Capability.BODY_COMPOSITION, options):
        entities.extend(
            EufyScaleCalculatedSensor(data, description, getter)
            for description, getter in CALCULATED_DESCRIPTIONS
        )

    async_add_entities(entities)
