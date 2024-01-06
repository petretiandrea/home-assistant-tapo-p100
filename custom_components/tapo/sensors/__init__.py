from custom_components.tapo.coordinators import TapoCoordinator
from custom_components.tapo.sensors.sensor_config import SensorConfig
from custom_components.tapo.sensors.tapo_sensor_source import TapoSensorSource
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.const import UnitOfEnergy
from homeassistant.const import UnitOfPower
from homeassistant.const import UnitOfTime
from homeassistant.helpers.typing import StateType
from plugp100.responses.device_state import DeviceInfo
from plugp100.responses.energy_info import EnergyInfo
from plugp100.responses.power_info import PowerInfo


class TodayEnergySensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "today energy",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfEnergy.KILO_WATT_HOUR,
        )

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        if coordinator.has_capability(EnergyInfo):
            return coordinator.get_state_of(EnergyInfo).today_energy / 1000
        return None


class MonthEnergySensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "month energy",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfEnergy.KILO_WATT_HOUR,
        )

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        if coordinator.has_capability(EnergyInfo):
            return coordinator.get_state_of(EnergyInfo).month_energy / 1000
        return None


# class ThisMonthEnergySensorSource(TapoSensorSource):
#     def get_config(self) -> SensorConfig:
#         return SensorConfig(
#             "this month energy",
#             DEVICE_CLASS_ENERGY,
#             STATE_CLASS_TOTAL_INCREASING,
#             ENERGY_KILO_WATT_HOUR,
#         )

#     def get_value(self, state: TapoDeviceState | None) -> StateType:
#         if state.energy_info is not None:
#             return state.energy_info.this_month_energy / 1000
#         return None


class CurrentEnergySensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "current power",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
            UnitOfPower.WATT,
        )

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        if coordinator.has_capability(EnergyInfo):
            return coordinator.get_state_of(EnergyInfo).current_power / 1000
        elif coordinator.has_capability(PowerInfo):
            return coordinator.get_state_of(PowerInfo).current_power
        return None


class SignalSensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            name="signal level",
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            state_class=None,
            unit_measure=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            is_diagnostic=True,
        )

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        try:
            return coordinator.get_state_of(DeviceInfo).rssi
        except Exception:  # pylint: disable=broad-except
            return 0


class TodayRuntimeSensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "today runtime",
            SensorDeviceClass.DURATION,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfTime.MINUTES,
        )

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        if coordinator.has_capability(EnergyInfo):
            sensor = coordinator.get_state_of(EnergyInfo)
            if sensor is not None:
                return sensor.today_runtime
        return None


class MonthRuntimeSensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "month runtime",
            SensorDeviceClass.DURATION,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfTime.MINUTES,
        )

    def get_value(self, coordinator: TapoCoordinator) -> StateType:
        if coordinator.has_capability(EnergyInfo):
            sensor = coordinator.get_state_of(EnergyInfo)
            if sensor is not None:
                return sensor.month_runtime
        return None
