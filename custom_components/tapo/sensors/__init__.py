from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.const import UnitOfEnergy
from homeassistant.const import UnitOfPower
from homeassistant.const import UnitOfTime
from homeassistant.helpers.typing import StateType
from plugp100.new.components.energy_component import EnergyComponent

from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.sensors.sensor_config import SensorConfig
from custom_components.tapo.sensors.tapo_sensor_source import TapoSensorSource


class TodayEnergySensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "today energy",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfEnergy.KILO_WATT_HOUR,
        )

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        if energy := coordinator.device.get_component(EnergyComponent):
            return energy.energy_info.today_energy / 1000
        return None


class MonthEnergySensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "month energy",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfEnergy.KILO_WATT_HOUR,
        )

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        if energy := coordinator.device.get_component(EnergyComponent):
            return energy.energy_info.month_energy / 1000
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

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        if energy := coordinator.device.get_component(EnergyComponent):
            return energy.energy_info.current_power / 1000 if energy.energy_info else energy.power_info.current_power
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

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        try:
            return coordinator.device.wifi_info.rssi
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

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        if energy := coordinator.device.get_component(EnergyComponent):
            return energy.energy_info.today_runtime if energy.energy_info else None
        return None


class MonthRuntimeSensorSource(TapoSensorSource):
    def get_config(self) -> SensorConfig:
        return SensorConfig(
            "month runtime",
            SensorDeviceClass.DURATION,
            SensorStateClass.TOTAL_INCREASING,
            UnitOfTime.MINUTES,
        )

    def get_value(self, coordinator: TapoDataCoordinator) -> StateType:
        if energy := coordinator.device.get_component(EnergyComponent):
            return energy.energy_info.month_runtime if energy.energy_info else None
        return None
