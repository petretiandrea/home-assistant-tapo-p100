from typing import Any, Optional

from plugp100.api.requests.tapo_request import TapoRequest
from plugp100.api.tapo_client import TapoClient
from plugp100.components.base import DeviceComponent
from plugp100.models.energy import EnergyInfo
from plugp100.models.power import PowerInfo



class ChildEnergyComponent(DeviceComponent):
    """Energy component for power strip child sockets.

    Fetches per-socket energy data via control_child since the plugp100
    library's EnergyComponent only polls the parent device directly.
    """

    def __init__(self, client: TapoClient, child_id: str):
        self._client = client
        self._child_id = child_id
        self._energy_info: Optional[EnergyInfo] = None
        self._power_info: Optional[PowerInfo] = None

    async def update(self, current_state: dict[str, Any] | None = None):
        energy = await self._client.control_child(self._child_id, TapoRequest.get_energy_usage())
        power = await self._client.control_child(self._child_id, TapoRequest.get_current_power())

        if energy.is_success():
            energy_dict = dict(energy.value)
            # get_current_power returns watts; multiply by 1000 to match the milliwatt
            # convention that EnergyInfo/CurrentEnergySensorSource expects.
            energy_dict["current_power"] = (power.value.get("current_power", 0) * 1000) if power.is_success() else 0
            self._energy_info = EnergyInfo(energy_dict)
        else:
            self._energy_info = None

        self._power_info = PowerInfo(power.value) if power.is_success() else None

    @property
    def energy_info(self) -> Optional[EnergyInfo]:
        return self._energy_info

    @property
    def power_info(self) -> Optional[PowerInfo]:
        return self._power_info
