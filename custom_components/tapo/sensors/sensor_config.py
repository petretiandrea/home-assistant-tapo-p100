from dataclasses import dataclass


@dataclass
class SensorConfig:
    name: str
    device_class: str
    state_class: str
    unit_measure: str
    is_diagnostic: bool = False
