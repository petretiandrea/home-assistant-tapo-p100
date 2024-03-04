import asyncio
from itertools import chain

from custom_components.tapo.const import DISCOVERY_TIMEOUT
from homeassistant.components import network
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
)
from plugp100.discovery.discovered_device import DiscoveredDevice
from plugp100.discovery.tapo_discovery import TapoDiscovery


async def discovery_tapo_devices(hass: HomeAssistant) -> dict[str, DiscoveredDevice]:
    loop = asyncio.get_event_loop()

    broadcast_addresses = await network.async_get_ipv4_broadcast_addresses(hass)
    print("Addresses ", broadcast_addresses)
    discovery_tasks = [
        loop.run_in_executor(
            None,
            lambda: list(
                TapoDiscovery.scan(timeout=DISCOVERY_TIMEOUT, broadcast=str(address))
            ),
        )
        for address in broadcast_addresses
    ]
    return {
        dr.format_mac(device.mac): device
        for device in chain(*await asyncio.gather(*discovery_tasks))
    }
