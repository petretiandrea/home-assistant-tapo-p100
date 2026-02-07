from homeassistant import exceptions


class DeviceNotSupported(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""


class UnsupportedEncryption(exceptions.HomeAssistantError):
    """Error to indicate device uses unsupported encryption (e.g. TPAP)."""

    def __init__(self, encrypt_type: str = "unknown", *args: object) -> None:
        self.encrypt_type = encrypt_type
        super().__init__(
            f"Device uses unsupported encryption protocol: {encrypt_type}",
            *args,
        )
