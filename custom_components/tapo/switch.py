from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from plugp100 import P100

from .const import DOMAIN

from .tapo_helper import TapoHelper, SUPPORTED_DEVICE_AS_SWITCH


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices):
    # get tapo helper
    helper: TapoHelper = hass.data[DOMAIN][entry.entry_id]

    if helper.get_model().lower() in SUPPORTED_DEVICE_AS_SWITCH:
        switch = P100Switch(helper)
        async_add_devices([switch], True)


class P100Switch(SwitchEntity):
    def __init__(self, tapo: TapoHelper):
        self.tapo: TapoHelper = tapo
        self._is_on = False
        self._name = "Unknown"

    @property
    def unique_id(self):
        return self._name

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    @property
    def should_poll(self):
        return True

    def turn_on(self):
        self.tapo.change_state(True)
        self._is_on = True

    def turn_off(self):
        self.tapo.change_state(False)
        self._is_on = False

    def update(self):
        current_state = self.tapo.get_state()
        self._is_on = current_state["device_on"]
        self._name = current_state["nickname"]