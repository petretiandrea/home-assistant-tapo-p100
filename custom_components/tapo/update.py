import logging
from datetime import timedelta
from typing import cast, Any, Optional

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature, UpdateDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.new.tapodevice import TapoDevice
from plugp100.responses.firmware import LatestFirmware, FirmwareDownloadProgress, FirmwareDownloadStatus
from plugp100.responses.tapo_exception import TapoException

from custom_components.tapo import DOMAIN, HassTapoDeviceData
from custom_components.tapo.coordinators import TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity

POLL_DELAY_IDLE = timedelta(seconds=6 * 60 * 60)
POLL_DELAY_UPGRADE = timedelta(seconds=60)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if data.coordinator.is_hub:
        coordinators = [
            TapoDeviceFirmwareDataCoordinator(hass, coordinator.device, POLL_DELAY_IDLE) \
            for coordinator in data.child_coordinators
        ]
    else:
        coordinators = [TapoDeviceFirmwareDataCoordinator(hass, data.coordinator.device, POLL_DELAY_IDLE)]

    async_add_entities([
        TapoDeviceFirmwareEntity(coordinator, coordinator.device) for coordinator in coordinators
    ], True)


class TapoDeviceFirmwareDataCoordinator(TapoDataCoordinator):

    def __init__(self, hass: HomeAssistant, device: TapoDevice, polling_interval: timedelta):
        super().__init__(hass, device, polling_interval)
        self._latest_firmware: Optional[LatestFirmware] = None
        self._download_status: Optional[FirmwareDownloadProgress] = None

    @property
    def latest_firmware(self) -> Optional[LatestFirmware]:
        return self._latest_firmware

    @property
    def download_progress(self) -> Optional[FirmwareDownloadProgress]:
        return self._download_status

    async def poll_update(self):
        self._latest_firmware = (await self.device.get_latest_firmware()).get_or_raise()
        self._download_status = (await self.device.get_firmware_download_state()).get_or_raise()
        if self._download_status.status == FirmwareDownloadStatus.DOWNLOADING or \
                self._download_status == FirmwareDownloadStatus.PREPARING:
            self.update_interval = POLL_DELAY_UPGRADE
        else:
            self.update_interval = POLL_DELAY_IDLE
        return self._latest_firmware


class TapoDeviceFirmwareEntity(CoordinatedTapoEntity, UpdateEntity):
    _attr_has_entity_name = True
    _attr_supported_features = (
            UpdateEntityFeature.INSTALL
            | UpdateEntityFeature.PROGRESS
            | UpdateEntityFeature.RELEASE_NOTES
    )
    _attr_device_class = UpdateDeviceClass.FIRMWARE

    coordinator: TapoDeviceFirmwareDataCoordinator

    def __init__(self, coordinator: TapoDeviceFirmwareDataCoordinator, device: TapoDevice):
        super().__init__(coordinator, device)
        self._attr_name = "Firmware"

    def release_notes(self) -> str | None:
        """Get the release notes for the latest update."""
        status = self.coordinator.latest_firmware
        if status.need_to_upgrade:
            return status.release_note
        return None

    async def async_install(
            self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install a firmware update."""
        try:
            result = (await self.device.start_firmware_upgrade())
        except TapoException as ex:
            raise HomeAssistantError("Unable to send Firmware update request. Check the controller is online.") from ex
        except Exception as ex:
            raise HomeAssistantError("Firmware update request rejected") from ex
        finally:
            await self.coordinator.async_request_refresh()

        if not result:
            raise HomeAssistantError(
                "Unable to send Firmware update request. Check the controller is online.")

    @property
    def installed_version(self) -> str | None:
        return self.device.firmware_version

    @property
    def latest_version(self) -> str | None:
        status = self.coordinator.latest_firmware
        return status.firmware_version \
            if status.firmware_version and status.need_to_upgrade \
            else self.device.firmware_version

    @property
    def in_progress(self) -> bool | int | None:
        download_progress = self.coordinator.download_progress
        return download_progress.download_in_progress if download_progress else 0

    @property
    def auto_update(self) -> bool:
        download_progress = self.coordinator.download_progress
        return download_progress.auto_upgrade if download_progress else False


_LOGGER = logging.getLogger(__name__)
